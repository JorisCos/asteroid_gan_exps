import os
import random
import soundfile as sf
import torch
import yaml
import json
import argparse
import pandas as pd
from tqdm import tqdm
from pprint import pprint

from asteroid.metrics import get_metrics
from asteroid_gan_exps.data.SEGAN_dataset import SEGAN
from asteroid.losses import PITLossWrapper, pairwise_neg_sisdr
from asteroid.utils.torch_utils import load_state_dict_in
from asteroid.utils import tensors_to_device
import numpy as np
from scipy import signal
from generator import make_generator_and_optimizer

parser = argparse.ArgumentParser()
parser.add_argument('--test_dir', type=str, default="data/wav16k/min/test",
                    help='Test directory including the csv files')
parser.add_argument('--use_gpu', type=int, default=0,
                    help='Whether to use the GPU for model execution')
parser.add_argument('--exp_dir', default='exp/tmp',
                    help='Experiment root')
parser.add_argument('--n_save_ex', type=int, default=10,
                    help='Number of audio examples to save, -1 means all')

compute_metrics = ['si_sdr', 'sdr', 'sir', 'sar', 'stoi']


def main(conf):
    # Make the model
    model, _, _ = make_generator_and_optimizer(conf['train_conf'])
    # Load best model
    with open(os.path.join(conf['exp_dir'], 'best_k_models.json'), "r") as f:
        best_k = json.load(f)
    best_model_path = min(best_k, key=best_k.get)
    # Load checkpoint
    checkpoint = torch.load(best_model_path, map_location='cpu')
    state = checkpoint['state_dict']
    state_copy = state.copy()
    # # Remove unwanted keys
    for keys, values in state.items():
        if keys.startswith('discriminator'):
            del state_copy[keys]
        if keys.startswith('generator'):
            state_copy[keys.replace('generator.', '')] = state_copy.pop(keys)

    model = load_state_dict_in(state_copy, model)
    # Handle device placement
    if conf['use_gpu']:
        model.cuda()
    model_device = next(model.parameters()).device
    test_set = SEGAN(csv_dir=conf['test_dir'],
                     task=conf['train_conf']['data']['task'],
                     sample_rate=conf['sample_rate'],
                     n_src=conf['train_conf']['data']['n_src'],
                     segment=None)  # Uses all segment length
    # Used to reorder sources only

    loss_func = PITLossWrapper(pairwise_neg_sisdr, pit_from='pw_mtx')

    # Randomly choose the indexes of sentences to save.
    eval_save_dir = os.path.join(conf['exp_dir'])
    ex_save_dir = os.path.join(eval_save_dir, 'examples/')
    if conf['n_save_ex'] == -1:
        conf['n_save_ex'] = len(test_set)
    save_idx = random.sample(range(len(test_set)), conf['n_save_ex'])
    series_list = []
    torch.no_grad().__enter__()
    for idx in tqdm(range(len(test_set))):
        # Forward the network on the mixture.
        mix, sources = tensors_to_device(test_set[idx], device=model_device)
        est_sources = torch.zeros_like(mix)
        for n_slice in range(mix.size(1)):
            est_sources[0, n_slice, :] = model(
                mix[0, n_slice, :].unsqueeze(0).unsqueeze(0))
        est_sources = de_slicer(est_sources, sources)
        sources = sources.unsqueeze(0)
        est_sources = est_sources.unsqueeze(0)
        loss, reordered_sources = loss_func(est_sources, sources,
                                            return_est=True)
        mix = de_slicer(mix, sources)
        mix_np = de_emphasis(mix.squeeze().cpu().data.numpy()).astype(
            'float32')
        sources_np = de_emphasis(sources.squeeze(0).cpu().data.numpy()).astype(
            'float32')
        est_sources_np = de_emphasis(
            reordered_sources.squeeze(0).cpu().data.numpy()).astype('float32')
        # For each utterance, we get a dictionary with the mixture path,
        # the input and output metrics
        utt_metrics = get_metrics(mix_np, sources_np, est_sources_np,
                                  sample_rate=conf['sample_rate'],
                                  metrics_list=compute_metrics)
        utt_metrics['mix_path'] = test_set.mixture_path
        series_list.append(pd.Series(utt_metrics))

        # Save some examples in a folder. Wav files and metrics as text.
        if idx in save_idx:
            local_save_dir = os.path.join(ex_save_dir, 'ex_{}/'.format(idx))
            os.makedirs(local_save_dir, exist_ok=True)
            sf.write(local_save_dir + "mixture.wav", mix_np,
                     conf['sample_rate'])
            # Loop over the sources and estimates
            for src_idx, src in enumerate(sources_np):
                sf.write(local_save_dir + "s{}.wav".format(src_idx), src,
                         conf['sample_rate'])
            for src_idx, est_src in enumerate(est_sources_np):
                sf.write(local_save_dir + "s{}_estimate.wav".format(src_idx),
                         est_src, conf['sample_rate'])
            # Write local metrics to the example folder.
            with open(local_save_dir + 'metrics.json', 'w') as f:
                json.dump(utt_metrics, f, indent=0)

    # Save all metrics to the experiment folder.
    all_metrics_df = pd.DataFrame(series_list)
    all_metrics_df.to_csv(os.path.join(eval_save_dir, 'all_metrics.csv'))

    # Print and save summary metrics
    final_results = {}
    for metric_name in compute_metrics:
        input_metric_name = 'input_' + metric_name
        ldf = all_metrics_df[metric_name] - all_metrics_df[input_metric_name]
        final_results[metric_name] = all_metrics_df[metric_name].mean()
        final_results[metric_name + '_imp'] = ldf.mean()
    print('Overall metrics :')
    pprint(final_results)
    with open(os.path.join(eval_save_dir, 'final_metrics.json'), 'w') as f:
        json.dump(final_results, f, indent=0)


def de_emphasis(signal_batch, emph_coeff=0.95) -> np.array:
    """
    De-emphasis operation given a batch of signal.
    Reverts the pre-emphasized signal.

    Args:
        signal_batch(np.array): batch of signals, represented as numpy arrays
        emph_coeff(float): emphasis coefficient

    Returns:
        result: de-emphasized signal batch
    """
    return signal.lfilter([1], [1, -emph_coeff], signal_batch)


def de_slicer(sources, original_shape, window=16384):
    """
    Reconstruct a sliced signal (inverse slice() function)
    """
    # Get the number of slices
    n_slices = sources.size()[1]
    # Create container
    reconstructed = torch.zeros((sources.size()[0], n_slices * window))
    # Fill with the slices
    for n_slice in range(n_slices):
        reconstructed[:,
        n_slice * window:(n_slice + 1) * window] += sources[:, n_slice, :]
    # Remove padding
    reconstructed = reconstructed[:, :original_shape.size()[-1]]
    return reconstructed


if __name__ == '__main__':
    args = parser.parse_args()
    arg_dic = dict(vars(args))
    # Load training config
    conf_path = os.path.join(args.exp_dir, 'conf_g.yml')
    with open(conf_path) as f:
        train_conf = yaml.safe_load(f)
    arg_dic['sample_rate'] = train_conf['data']['sample_rate']
    arg_dic['train_conf'] = train_conf
    main(arg_dic)
