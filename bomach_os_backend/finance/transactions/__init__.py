"""Finance-owned transaction source package.

Submodules are intentionally not eagerly imported here. Historical `services`
and `user` Django apps load the compatibility modules that register these
models under their preserved app labels.
"""
