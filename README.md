# Asteroid GAN exps

In this repository you will find a minimal setup for training GANs using [Asteroid](https://github.com/mpariente/asteroid).

All experiments are conducted on [LibriMix](https://github.com/JorisCos/LibriMix).
# Installation

```bash
git clone https://github.com/JorisCos/asteroid_gan_exps
cd asteroid_gan_exps
pip install -e .
```

# Available recipes
* [x] [SEGAN](./egs/SEGAN) ([Pasxual et al.](https://arxiv.org/pdf/1703.09452.pdf))
* [x] [MetricGAN](./egs/MetricGAN) ([Fu et al.](https://arxiv.org/pdf/1905.04874.pdf)) 

## Citing Asteroid
```BibTex
@inproceedings{Pariente2020Asteroid,
    title={Asteroid: the {PyTorch}-based audio source separation toolkit for researchers},
    author={Manuel Pariente and Samuele Cornell and Joris Cosentino and Sunit Sivasankaran and
            Efthymios Tzinis and Jens Heitkaemper and Michel Olvera and Fabian-Robert Stöter and
            Mathieu Hu and Juan M. Martín-Doñas and David Ditter and Ariel Frank and Antoine Deleforge
            and Emmanuel Vincent},
    year={2020},
    booktitle={Proc. Interspeech},
}
```
