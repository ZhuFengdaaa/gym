from gym import utils
from gym import Env


class ProxyEnv(Env, utils.EzPickle):
    def __init__(self, wrapped_env):
        utils.EzPickle.__init__(self)
        self._wrapped_env = wrapped_env

    @property
    def wrapped_env(self):
        return self._wrapped_env

    def update(self, wrapped_env):
        self._wrapped_env = wrapped_env

    def reset(self, **kwargs):
        return self._wrapped_env.reset(**kwargs)

    @property
    def action_space(self):
        return self._wrapped_env.action_space

    @property
    def observation_space(self):
        return self._wrapped_env.observation_space

    def step(self, action):
        return self._wrapped_env.step(action)

    def seed(self, seed=None):
        return self._wrapped_env.seed(seed)

    def render(self, *args, **kwargs):
        return self._wrapped_env.render(*args, **kwargs)

    def log_diagnostics(self, paths, *args, **kwargs):
        self._wrapped_env.log_diagnostics(paths, *args, **kwargs)

    @property
    def horizon(self):
        return self._wrapped_env.horizon

    def terminate(self):
        self._wrapped_env.terminate()

    def get_param_values(self):
        return self._wrapped_env.get_param_values()

    def set_param_values(self, params):
        self._wrapped_env.set_param_values(params)
