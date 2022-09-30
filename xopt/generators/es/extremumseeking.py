import logging
import numpy as np
import pandas as pd
from xopt.generator import Generator, GeneratorOptions
logger = logging.getLogger(__name__)


class ExtremumSeekingOptions(GeneratorOptions):
    k: float = 2.0
    oscillation_size: float = 0.1
    decay_rate: float = 1.0


class ExtremumSeekingGenerator(Generator):
    """
    Extremum seeking algorithm.

    This algorithm must be stepped serially.
    """

    alias = "extremum_seeking"

    @staticmethod
    def default_options() -> ExtremumSeekingOptions:
        return ExtremumSeekingOptions()

    def __init__(self, vocs, options: ExtremumSeekingOptions = None):
        options = options or ExtremumSeekingOptions()
        if not isinstance(options, ExtremumSeekingOptions):
            raise ValueError("options must be a ExtremumSeekingOptions object")

        if vocs.n_objectives != 1:
            raise ValueError("vocs must have one objective for optimization")

        super().__init__(vocs, options)
        self.nES = len(vocs.variables)
        self.wES = np.linspace(1.0, 1.75, int(np.ceil(self.nES / 2)))
        self.dtES = 2 * np.pi / (10 * np.max(self.wES))
        self.aES = np.zeros(self.nES)
        for n in np.arange(self.nES):
            jw = int(np.floor(n / 2))
            self.aES[n] = self.wES[jw] * (options.oscillation_size) ** 2
        bound_low, bound_up = vocs.bounds
        self.p_ave = (bound_up + bound_low) / 2
        self.p_diff = bound_up - bound_low

    def add_data(self, new_data: pd.DataFrame):
        self.data = pd.concat([self.data, new_data], axis=0)

    # Function that normalizes paramters
    def p_normalize(self, p):
        p_norm = 2.0 * (p - self.p_ave) / self.p_diff
        return p_norm

    # Function that un-normalizes parameters
    def p_un_normalize(self, p):
        p_un_norm = p * self.p_diff/2.0 + self.p_ave
        return p_un_norm

    def get_last_input_data(self):
        return self.data[self.vocs.variable_names].to_numpy()[-1]

    def get_last_outcome_data(self):
        return self.data[self.vocs.output_names].to_numpy()[-1]

    def generate(self, n_candidates) -> pd.DataFrame:
        if n_candidates != 1:
            raise NotImplementedError(
                "extremum seeking can only produce one candidate at a time"
            )

        # Initial data point
        if self.data.empty:
            return pd.DataFrame(dict(zip(self.vocs.variable_names, self.p_ave.reshape(-1, 1))))

        p_n = self.p_normalize(self.get_last_input_data())
        cES_now = self.get_last_outcome_data()[0]
        i = len(self.data) - 1
        amplitude = self.options.decay_rate ** i

        # ES step for each parameter
        p_next_n = np.zeros(self.nES)

        # Loop through each parameter
        for j in np.arange(self.nES):
            # Use the same frequency for each two parameters
            # Alternating Sine and Cosine
            jw = int(np.floor(j/2))
            if (-1)**j > 0:
                p_next_n[j] = p_n[j] + amplitude * self.dtES * \
                    np.cos(self.dtES * i * self.wES[jw] + self.options.k * cES_now) * \
                        (self.aES[j] * self.wES[jw]) ** 0.5
            else:
                p_next_n[j] = p_n[j] + amplitude * self.dtES * \
                    np.sin(self.dtES * i * self.wES[jw] + self.options.k * cES_now) * \
                        (self.aES[j] * self.wES[jw]) ** 0.5

            # For each new ES value, check that we stay within min/max constraints
            if p_next_n[j] < -1.0:
                p_next_n[j] = -1.0
            if p_next_n[j] > 1.0:
                p_next_n[j] = 1.0

        p_next = self.p_un_normalize(p_next_n)

        # Return the next value
        return pd.DataFrame(dict(zip(self.vocs.variable_names, p_next.reshape(-1, 1))))
