import logging
import os
from datetime import datetime, timedelta
from textwrap import dedent

import numpy as np

from core.loaders.ascii import ASCIIEncoder
from core.loaders.fieldset import Fieldset
from core.loaders.geopoints import read_geopoints

from ..computations.models import Computer
from .log_factory import (
    general_parameters_logs,
    observations_logs,
    output_file_logs,
    point_data_table_logs,
    predictand_logs,
    predictors_logs,
)
from .utils import iter_daterange

logging.basicConfig(
    filename=f'{os.environ["HOME"]}/ecpoint.logs', filemode="w", level=logging.INFO
)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
logging.getLogger("").addHandler(console)


def run(config):
    BaseDateS = config.parameters.date_start
    BaseDateF = config.parameters.date_end
    acc = config.predictand.accumulation
    spinup_limit = config.parameters.spinup_limit
    PathOBS = config.observations.path
    PathFC = config.predictors.path
    PathPredictand = config.predictand.path
    PathOUT = config.parameters.out_path

    # Set up the input/output parameters
    BaseDateS = datetime.strptime(BaseDateS, "%Y%m%d").date()
    BaseDateF = datetime.strptime(BaseDateF, "%Y%m%d").date()
    BaseDateSSTR = BaseDateS.strftime("%Y%m%d")
    BaseDateFSTR = BaseDateF.strftime("%Y%m%d")

    computations = config.computations

    serializer = ASCIIEncoder(path=PathOUT)

    header = dedent(
        f"""
        # THIS IS AN AUTOGENERATED FILE. DO NOT EDIT THIS FILE DIRECTLY.
        #
        # Created on {datetime.now()}.
        #
        # """  # Do NOT strip
    )

    header += "\n# ".join(general_parameters_logs(config).split("\n"))
    header += "\n# ".join(predictand_logs(config).split("\n"))
    header += "\n# ".join(predictors_logs(config).split("\n"))
    header += "\n# ".join(observations_logs(config).split("\n"))
    header += "\n# ".join(output_file_logs(config).split("\n"))
    header += "\n# ".join(point_data_table_logs().split("\n"))

    serializer.add_header(header.strip())

    #############################################################################################

    # PROCESSING MODEL DATA

    logging.info(
        dedent(
            """
        ************************************
        ecPoint-Calibrate - POINT DATA TABLE
        ************************************
    """
        )
    )

    logging.info(general_parameters_logs(config))
    logging.info(predictand_logs(config))
    logging.info(predictors_logs(config))
    logging.info(observations_logs(config))
    logging.info(output_file_logs(config))
    logging.info(point_data_table_logs())

    logging.info("*** START COMPUTATIONS ***")

    # Counter for the BaseDate and BaseTime to avoid repeating the same forecasts in different cases
    counter_used_FC = {}
    obsTOT = 0
    obsUSED = 0
    model_interval = config.parameters.model_interval
    step_interval = config.parameters.step_interval
    BaseTimeS = config.parameters.start_time
    predictand_min_value = (
        config.predictand.min_value + config.computations[0].addScale
    ) * config.computations[0].mulScale
    predictand_scaled_units = config.observations.units

    logging.info(
        "The start step of the acc period (StepS) is considered between 'LimSU+1' "
        "(to avoid the spin-up window), and 'IntBT+LimSU' (to consider the shortest range forecast available)."
    )
    logging.info(
        f"Therefore, StepS will range between t+{spinup_limit+1} and t+{model_interval + spinup_limit}"
    )

    for curr_date, curr_time, step_s, case in iter_daterange(
        start_date=BaseDateS,
        end_date=BaseDateF,
        start_hour=BaseTimeS,
        model_interval=model_interval,
        step_interval=step_interval,
        spinup_limit=spinup_limit,
    ):
        logging.info("")
        if case != 1:
            logging.info("**********")
        logging.info(f"Case {case}")
        logging.info("FORECAST PARAMETERS:")

        if config.predictand.is_accumulated:
            forecast = f'{curr_date.strftime("%Y%m%d")}, {curr_time:02d} UTC, (t+{step_s}, t+{step_s + acc})'
        else:
            forecast = (
                f'{curr_date.strftime("%Y%m%d")}, {curr_time:02d} UTC, (t+{step_s})'
            )

        logging.info(f"  {forecast}")

        if forecast in counter_used_FC:
            logging.warn(
                f"  The above forecast was already considered for computation in Case {counter_used_FC[forecast]}"
            )
            continue

        # Reading the forecasts
        if curr_date < BaseDateS or curr_date > BaseDateF:
            logging.warn(
                f"  Forecast out of the calibration period {BaseDateSSTR} - {BaseDateFSTR}. Forecast not considered."
            )
            continue

        counter_used_FC[forecast] = case
        logging.info("")

        def get_grib_path(predictor_code, step):
            file_name = "_".join(
                [
                    predictor_code,
                    curr_date.strftime("%Y%m%d"),
                    f"{curr_time:02d}",
                    f"{step:02d}",
                ]
            )
            file_ext = "grib"
            return (
                PathFC
                / predictor_code
                / (curr_date.strftime("%Y%m%d") + f"{curr_time:02d}")
                / f"{file_name}.{file_ext}"
            )

        # Note about the computation of the sr.
        # The solar radiation is a cumulative variable and its units is J/m2 (which means, W*s/m2).
        # One wants the 24h. The 24h mean is obtained by taking the difference between the beginning and the end of the 24 hourly period
        # and dividing by the number of seconds in that period (24h = 86400 sec). Thus, the unit will be W/m2

        # Defining the parameters for the rainfall observations
        validDateF = (
            datetime.combine(curr_date, datetime.min.time())
            + timedelta(hours=curr_time)
            + timedelta(hours=step_s + acc)  # step_s + 0 for instantaneous predictand
        )
        DateVF = validDateF.strftime("%Y%m%d")
        HourVF = validDateF.strftime("%H")
        HourVF_num = validDateF.hour
        logging.info("OBSERVATIONS PARAMETERS:")

        if config.predictand.is_accumulated:
            logging.info(f"  Validity date/time (end of {acc} h period) = {validDateF}")
        else:
            logging.info(f"  Validity date/time = {validDateF}")

        if config.predictand.is_accumulated:
            obs_path = (
                PathOBS
                / f"acc{acc:02}h"
                / DateVF
                / f"tp_{acc:02d}_{DateVF}_{HourVF}.geo"
            )
        else:
            obs_path = PathOBS / DateVF / f"tp_{DateVF}_{HourVF}.geo"

        # Reading Rainfall Observations
        logging.info(f"  Read observation file: {os.path.basename(obs_path)}")
        try:
            obs = read_geopoints(path=obs_path)
        except IOError:
            logging.warn(f"  Observation file not found in DB: {obs_path}.")
            continue
        except Exception:
            logging.error(
                f"  Error reading observation file: {os.path.basename(obs_path)}"
            )
            continue

        nOBS = len(obs)

        if nOBS == 0:
            logging.warn(
                f"  No observation in the file: {os.path.basename(obs_path)}. Forecast not considered."
            )
            continue

        obsTOT += nOBS

        # Set is_reference attribute for each computation
        for computation in computations:
            computation.is_reference = (
                len(computation.inputs) == 1
                and computation.inputs[0]["code"] == config.predictand.code
            )

        # Step generation and adjustment
        if config.predictand.is_accumulated:
            steps = list(
                range(step_s, step_s + acc, config.predictors.sampling_interval)
            )

            # Make senses to compute (accumulated) Solar Radiation for only accumulated predictand.
            if acc == 24:
                step_start_sr, step_end_sr = steps[0], steps[-1]
            else:
                if steps[-1] <= 24:
                    step_start_sr, step_end_sr = 0, 24
                else:
                    step_start_sr, step_end_sr = steps[-1] - 24, steps[-1]
        else:
            steps = [step_s]

        logging.info("")
        logging.info("PREDICTORS COMPUTATIONS:")

        base_fields = set(config.predictors.codes)

        derived_computations = [
            computation
            for computation in computations
            if ({input["code"] for input in computation.inputs} - base_fields != set())
            and computation.isPostProcessed
            and computation.field != "LOCAL_SOLAR_TIME"
        ]

        # We want to compute the predictand computation, followed by other
        # independent computations in order to populate the cache and use it
        # for derived computations.
        base_computations = sorted(
            [
                computation
                for computation in computations
                if computation not in derived_computations
                and computation.field != "LOCAL_SOLAR_TIME"
            ],
            key=lambda computation: computation.is_reference,
            reverse=True,
        )

        computations_cache = {}
        computations_result = []
        skip = False

        for computation in base_computations:
            computer = Computer(computation)

            # Base computations normally shouldn't have more than one
            # predictor input
            predictor_code = computer.computation.inputs[0]["code"]

            steps = (
                [step_start_sr, step_end_sr]
                if computation.field == "24H_SOLAR_RADIATION"
                else steps
            )

            computation_steps = []

            paths_to_read = Computer.filter_paths_to_read(
                paths=[get_grib_path(predictor_code, step) for step in steps],
                computation=computation.field,
            )

            for path in paths_to_read:
                logging.info(f"  Reading forecast file: {os.path.basename(path)}")

                try:
                    fieldset = Fieldset.from_path(path=path)
                except IOError:
                    logging.warn(f"  Forecast file not found: {path}.")
                    skip = True
                    break
                except Exception:
                    logging.error(f"  Reading forecast file failed: {path}.")
                    skip = True
                    break
                else:
                    computation_steps.append(fieldset)

            if skip:
                break

            logging.info(
                f"  Computing {computer.computation.fullname} using "
                f"{len(computation_steps)} input(s)."
            )

            computed_value = computer.run(*computation_steps)
            computations_cache[computation.shortname] = computed_value

            # A base computation that is not post-processed, probably serves
            # the only purpose of an input for a (future) derived computation.
            if not computation.isPostProcessed:
                continue

            logging.info("  Selecting the nearest grid point to observations.")
            geopoints = computed_value.nearest_gridpoint(obs)

            if computation.is_reference:
                ref_code = computation.shortname
                if config.predictand.is_accumulated:
                    mask = geopoints >= predictand_min_value
                    logging.info(
                        f"  Selecting values that correspond to {computation.shortname}"
                        f" >= {predictand_min_value} {predictand_scaled_units}/{acc}h."
                    )
                    ref_geopoints = geopoints.filter(mask)
                else:
                    ref_geopoints = geopoints

                if not ref_geopoints:
                    if config.predictand.is_accumulated:
                        logging.warn(
                            f"  The observation file does not contain observations that correspond to "
                            f" {computation.shortname} >= "
                            f"{predictand_min_value} {predictand_scaled_units}/{acc}h."
                        )
                    else:
                        # [TODO] - Add a specific logger message
                        pass

                    skip = True
                    break

                computations_result.append(
                    (
                        computation.shortname,
                        np.around(ref_geopoints.values(), decimals=3),
                    )
                )
            else:
                if config.predictand.is_accumulated:
                    geopoints = geopoints.filter(mask)

                computations_result.append(
                    (computation.shortname, np.around(geopoints.values(), decimals=3))
                )

            logging.info("")

        if skip:
            continue

        for computation in derived_computations:
            computer = Computer(computation)
            steps = [
                computations_cache[field_input["code"]]
                for field_input in computation.inputs
            ]

            input_codes = [field_input["code"] for field_input in computation.inputs]
            logging.info(
                f"  Computing {computer.computation.fullname} using "
                f"{len(computation.inputs)} input(s): {', '.join(input_codes)}."
            )

            if computation.field == "RATIO_FIELD":
                dividend, divisor = steps
                if config.predictand.is_accumulated:
                    computed_value = computer.run(
                        dividend.nearest_gridpoint(obs).filter(mask).values(),
                        divisor.nearest_gridpoint(obs).filter(mask).values(),
                    )
                else:
                    computed_value = (
                        computer.run(dividend.values, divisor.values)
                        .nearest_gridpoint(obs)
                        .values()
                    )
                computations_result.append(
                    (computation.shortname, np.around(computed_value, decimals=3))
                )
            else:
                computed_value = computer.run(*steps)
                computations_result.append(
                    (
                        computation.shortname,
                        np.around(
                            computed_value.nearest_gridpoint(obs).filter(mask).values()
                            if config.predictand.is_accumulated
                            else computed_value.nearest_gridpoint(obs).values(),
                            decimals=3,
                        ),
                    )
                )

        # Compute other parameters
        if config.predictand.is_accumulated:
            obs = obs.filter(mask)

        latObs = obs.latitudes()
        lonObs = obs.longitudes()

        vals_errors = []

        logging.info(f"  Computing the {config.predictand.error}.")
        if config.predictand.error == "FER":
            FER = ((obs - ref_geopoints) / ref_geopoints).values()
            vals_errors.append(("FER", np.around(FER, decimals=3)))

        if config.predictand.error == "FE":
            FE = (obs - ref_geopoints).values()
            vals_errors.append(("FE", np.around(FE, decimals=3)))

        LST_computation = next(
            (
                computation
                for computation in computations
                if computation.field == "LOCAL_SOLAR_TIME"
            ),
            None,
        )
        if LST_computation and LST_computation.isPostProcessed:
            vals_LST = [
                (
                    "LST",
                    np.around(
                        Computer(LST_computation).run(lonObs, HourVF_num), decimals=3
                    ),
                )
            ]
        else:
            vals_LST = []

        # Saving the output file in ascii format
        n = len(obs)
        obsUSED += n
        logging.info("")
        logging.info("POINT DATA TABLE:")
        logging.info(f"  Saving the point data table to output file: {PathOUT}")

        columns = (
            [
                ("BaseDate", [curr_date] * n),
                ("BaseTime", [curr_time] * n),
                (
                    "StepF" if config.predictand.is_accumulated else "Step",
                    [step_s + acc] * n,
                ),
                ("DateOBS", [DateVF] * n),
                ("TimeOBS", [HourVF] * n),
            ]
            + vals_LST
            + [
                ("LatOBS", latObs),
                ("LonOBS", lonObs),
                ("OBS", obs.values()),
                ("Predictand", np.around(ref_geopoints.values(), decimals=3)),
            ]
            + vals_errors
            + computations_result
        )

        serializer.add_columns_chunk(columns)

    logging.info(f"No of observations considered in the calibration period: {obsTOT}")
    if config.predictand.is_accumulated:
        logging.info(
            f"No of observations that correspond to {ref_code} >= {predictand_min_value} {predictand_scaled_units}/{acc}h: {obsUSED}"
        )

    if config.predictand.is_accumulated:
        footer = dedent(
            f"""
            # No of observations considered in the calibration period: {obsTOT}
            # No of observations that correspond to {ref_code} >= {predictand_min_value} {predictand_scaled_units}/{acc}h: {obsUSED}
            """
        ).strip()
    else:
        footer = f"# No of observations considered in the calibration period: {obsTOT}"

    serializer.add_footer(footer)
