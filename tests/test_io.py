from xopt import Evaluator, Xopt
from xopt.generators import RandomGenerator
from xopt.resources.testing import TEST_VOCS_BASE
from xopt.io import state_to_dict, read_config_dict
from xopt.evaluator import EvaluatorOptions


def dummy():
    pass


class Test_IO:
    def test_state_to_dict(self):
        evaluator = Evaluator.from_options(EvaluatorOptions(function=dummy))
        generator = RandomGenerator(TEST_VOCS_BASE)

        X = Xopt(generator=generator, evaluator=evaluator, vocs=TEST_VOCS_BASE)
        state_dict = state_to_dict(X)
        assert state_dict["generator"]["name"] == generator.options.__config__.title

        # read from dict
        gen, ev, vcs, options = read_config_dict(state_dict)
        assert ev.options.function == dummy

