from typing import Dict, List

import pandas as pd
import torch
from botorch.acquisition.multi_objective import qNoisyExpectedHypervolumeImprovement
from pydantic import Field

from xopt.generators.bayesian.objectives import (
    create_constraint_callables,
    create_mobo_objective,
)
from xopt.generators.ga.cnsga import CNSGAGenerator, CNSGAOptions

from xopt.vocs import VOCS
from .bayesian_generator import BayesianGenerator
from .options import AcqOptions, BayesianOptions


class MGGPOAcqOptions(AcqOptions):
    reference_point: Dict[str, float] = Field(
        None, description="dict of reference points for multi-objective optimization"
    )
    population_size: int = Field(64, description="population size for ga")


class MGGPOOptions(BayesianOptions):
    acq = MGGPOAcqOptions()


class MGGPOGenerator(BayesianGenerator):
    alias = "mggpo"

    def __init__(self, vocs: VOCS, options: MGGPOOptions = MGGPOOptions()):
        if not isinstance(options, MGGPOOptions):
            raise ValueError("options must be a MGGPOOptions object")

        super().__init__(vocs, options)

        # create GA generator
        self.ga_generator = CNSGAGenerator(
            vocs,
            options=CNSGAOptions(population_size=self.options.acq.population_size),
        )

    @staticmethod
    def default_options() -> MGGPOOptions:
        return MGGPOOptions()

    def generate(self, n_candidates: int) -> List[Dict]:
        if self.data.empty:
            return self.vocs.random_inputs(self.options.n_initial)
        else:
            ga_candidates = self.ga_generator.generate(n_candidates * 10)
            ga_candidates = pd.DataFrame(ga_candidates)[
                self.vocs.variable_names
            ].to_numpy()
            ga_candidates = torch.tensor(ga_candidates).reshape(
                -1, 1, self.vocs.n_variables
            )

            # evaluate the acquisition function on the ga candidates
            self.train_model()
            acq_funct = self.get_acquisition(self.model)
            acq_funct_vals = acq_funct(ga_candidates)
            best_idxs = torch.argsort(acq_funct_vals, descending=True)[:n_candidates]

            candidates = ga_candidates[best_idxs]
            return self.vocs.convert_numpy_to_inputs(
                candidates.reshape(n_candidates, self.vocs.n_variables).numpy()
            )

    def add_data(self, new_data: pd.DataFrame):
        super().add_data(new_data)
        self.ga_generator.add_data(self.data)

    def _get_objective(self):
        return create_mobo_objective(self.vocs)

    @property
    def reference_point(self):
        return torch.tensor(
            [-self.options.acq.reference_point[ele] for ele in
             self.vocs.objective_names],
            **self._tkwargs
        )

    def _get_acquisition(self, model):
        # get reference point from data
        inputs = self.get_input_data(self.data)

        # get list of constraining functions
        constraint_callables = create_constraint_callables(self.vocs)

        acq = qNoisyExpectedHypervolumeImprovement(
            model,
            X_baseline=inputs,
            prune_baseline=True,
            constraints=constraint_callables,
            ref_point=self.reference_point,
            sampler=self.sampler,
            objective=self.objective,
        )

        return acq
