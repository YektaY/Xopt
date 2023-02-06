import yaml
from botorch.acquisition import qUpperConfidenceBound
from pydantic import Field

from xopt.generators.bayesian.bayesian_generator import BayesianGenerator
from xopt.generators.bayesian.custom_botorch.constrained_acqusition import (
    ConstrainedMCAcquisitionFunction,
)
from xopt.generators.bayesian.objectives import (
    create_constraint_callables,
    create_mc_objective,
)
from xopt.generators.bayesian.options import AcqOptions, BayesianOptions
from xopt.generators.bayesian.time_dependent import (
    TDAcqOptions,
    TDModelOptions,
    TimeDependentBayesianGenerator,
)
from xopt.pydantic import get_descriptions_defaults
from xopt.vocs import VOCS


class UpperConfidenceBoundOptions(AcqOptions):
    beta: float = Field(2.0, description="Beta parameter for UCB optimization")


class TDUpperConfidenceBoundOptions(TDAcqOptions):
    beta: float = Field(2.0, description="Beta parameter for UCB optimization")


class UCBOptions(BayesianOptions):
    acq = UpperConfidenceBoundOptions()


class TDUCBOptions(UCBOptions):
    acq = TDUpperConfidenceBoundOptions()
    model = TDModelOptions()


def format_option_descriptions(options_dict):
    return "\n\nGenerator Options\n" + yaml.dump(options_dict)


class UpperConfidenceBoundGenerator(BayesianGenerator):
    alias = "upper_confidence_bound"
    __doc__ = (
        """Implements Bayeisan Optimization using the Upper Confidence Bound 
    acquisition function"""
        + f"{format_option_descriptions(get_descriptions_defaults(UCBOptions()))}"
    )

    def __init__(self, vocs: VOCS, options: UCBOptions = None):
        """
        Generator using UpperConfidenceBound acquisition function

        Parameters
        ----------
        vocs: dict
            Standard vocs dictionary for xopt

        options: UpperConfidenceBoundOptions
            Specific options for this generator
        """
        options = options or UCBOptions()
        if not isinstance(options, UCBOptions):
            raise ValueError("options must be a UCBOptions object")

        if vocs.n_objectives != 1:
            raise ValueError("vocs must have one objective for optimization")

        super().__init__(vocs, options)

    @staticmethod
    def default_options() -> UCBOptions:
        return UCBOptions()

    def _get_objective(self):
        return create_mc_objective(self.vocs)

    def _get_acquisition(self, model):
        qUCB = qUpperConfidenceBound(
            model,
            sampler=self.sampler,
            objective=self.objective,
            beta=self.options.acq.beta,
        )

        cqUCB = ConstrainedMCAcquisitionFunction(
            model,
            qUCB,
            create_constraint_callables(self.vocs),
        )

        return cqUCB


class TDUpperConfidenceBoundGenerator(
    TimeDependentBayesianGenerator, UpperConfidenceBoundGenerator
):
    alias = "time_dependent_upper_confidence_bound"

    def __init__(self, vocs: VOCS, options: TDUCBOptions = None):
        options = options or TDUCBOptions()
        if not isinstance(options, UCBOptions):
            raise ValueError("options must be a TDUCBOptions object")

        super(TDUpperConfidenceBoundGenerator, self).__init__(vocs, options)

    @staticmethod
    def default_options() -> TDUCBOptions:
        return TDUCBOptions()
