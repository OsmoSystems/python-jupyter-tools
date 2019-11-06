import pkg_resources

import pandas as pd
import pytest

import osmo_jupyter.dataset.combine as module


@pytest.fixture
def test_picolog_file_path():
    return pkg_resources.resource_filename(
        "osmo_jupyter", "test_fixtures/test_picolog.csv"
    )


@pytest.fixture
def test_calibration_file_path():
    return pkg_resources.resource_filename(
        "osmo_jupyter", "test_fixtures/test_calibration_log.csv"
    )


class TestOpenAndCombineSensorData:
    def test_interpolates_data_correctly(
        self, test_calibration_file_path, test_picolog_file_path
    ):
        combined_data = module.open_and_combine_picolog_and_calibration_data(
            calibration_log_filepaths=[test_calibration_file_path],
            picolog_log_filepaths=[test_picolog_file_path],
        ).reset_index()  # move timestamp index to a column

        # calibration log has 23 columns, but we only need to check that picolog data is interpolated correctly
        subset_combined_data_to_compare = combined_data[
            [
                "timestamp",
                "equilibration status",
                "setpoint temperature (C)",
                "PicoLog temperature (C)",
            ]
        ]

        expected_interpolation = pd.DataFrame(
            [
                {
                    "timestamp": "2019-01-01 00:00:00",
                    "equilibration status": "waiting",
                    "setpoint temperature (C)": 40,
                    "PicoLog temperature (C)": 39,
                },
                {
                    "timestamp": "2019-01-01 00:00:01",
                    "equilibration status": "equilibrated",
                    "setpoint temperature (C)": 40,
                    "PicoLog temperature (C)": 39.5,
                },
                {
                    "timestamp": "2019-01-01 00:00:03",
                    "equilibration status": "equilibrated",
                    "setpoint temperature (C)": 40,
                    "PicoLog temperature (C)": 40,
                },
                {
                    "timestamp": "2019-01-01 00:00:04",
                    "equilibration status": "waiting",
                    "setpoint temperature (C)": 40,
                    "PicoLog temperature (C)": 40,
                },
            ]
        ).astype(
            subset_combined_data_to_compare.dtypes
        )  # coerce datatypes to match

        pd.testing.assert_frame_equal(
            subset_combined_data_to_compare, expected_interpolation
        )


class TestGetEquilibrationBoundaries:
    @pytest.mark.parametrize(
        "input_equilibration_status, expected_boundaries",
        [
            (
                {  # Use full timestamps to show that it works at second resolution
                    pd.to_datetime("2019-01-01 00:00:00"): "waiting",
                    pd.to_datetime("2019-01-01 00:00:01"): "equilibrated",
                    pd.to_datetime("2019-01-01 00:00:02"): "equilibrated",
                    pd.to_datetime("2019-01-01 00:00:03"): "waiting",
                },
                [
                    {
                        "start_time": pd.to_datetime("2019-01-01 00:00:01"),
                        "end_time": pd.to_datetime("2019-01-01 00:00:02"),
                    }
                ],
            ),
            (
                {  # Switch to using only years as the timestamp for terseness and readability
                    pd.to_datetime("2019"): "waiting",
                    pd.to_datetime("2020"): "equilibrated",
                    pd.to_datetime("2021"): "waiting",
                },
                [
                    {
                        "start_time": pd.to_datetime("2020"),
                        "end_time": pd.to_datetime("2020"),
                    }
                ],
            ),
            (
                {
                    pd.to_datetime("2020"): "equilibrated",
                    pd.to_datetime("2021"): "waiting",
                    pd.to_datetime("2022"): "equilibrated",
                    pd.to_datetime("2023"): "waiting",
                },
                [
                    {
                        "start_time": pd.to_datetime("2020"),
                        "end_time": pd.to_datetime("2020"),
                    },
                    {
                        "start_time": pd.to_datetime("2022"),
                        "end_time": pd.to_datetime("2022"),
                    },
                ],
            ),
            (
                {
                    pd.to_datetime("2019"): "waiting",
                    pd.to_datetime("2020"): "equilibrated",
                    pd.to_datetime("2021"): "waiting",
                    pd.to_datetime("2022"): "equilibrated",
                },
                [
                    {
                        "start_time": pd.to_datetime("2020"),
                        "end_time": pd.to_datetime("2020"),
                    },
                    {
                        "start_time": pd.to_datetime("2022"),
                        "end_time": pd.to_datetime("2022"),
                    },
                ],
            ),
            (
                {
                    pd.to_datetime("2019"): "waiting",
                    pd.to_datetime("2020"): "equilibrated",
                    pd.to_datetime("2021"): "waiting",
                    pd.to_datetime("2022"): "equilibrated",
                    pd.to_datetime("2023"): "waiting",
                },
                [
                    {
                        "start_time": pd.to_datetime("2020"),
                        "end_time": pd.to_datetime("2020"),
                    },
                    {
                        "start_time": pd.to_datetime("2022"),
                        "end_time": pd.to_datetime("2022"),
                    },
                ],
            ),
            (
                {
                    pd.to_datetime("2019"): "equilibrated",
                    pd.to_datetime("2020"): "waiting",
                },
                [
                    {
                        "start_time": pd.to_datetime("2019"),
                        "end_time": pd.to_datetime("2019"),
                    }
                ],
            ),
            (
                {
                    pd.to_datetime("2019"): "waiting",
                    pd.to_datetime("2020"): "equilibrated",
                },
                [
                    {
                        "start_time": pd.to_datetime("2020"),
                        "end_time": pd.to_datetime("2020"),
                    }
                ],
            ),
            (
                {
                    pd.to_datetime("2019"): "equilibrated",
                    pd.to_datetime("2020"): "waiting",
                    pd.to_datetime("2021"): "equilibrated",
                },
                [
                    {
                        "start_time": pd.to_datetime("2019"),
                        "end_time": pd.to_datetime("2019"),
                    },
                    {
                        "start_time": pd.to_datetime("2021"),
                        "end_time": pd.to_datetime("2021"),
                    },
                ],
            ),
        ],
    )
    def test_finds_correct_edges(self, input_equilibration_status, expected_boundaries):

        parsed_equilibration_boundaries = module.get_equilibration_boundaries(
            equilibration_status=pd.Series(input_equilibration_status)
        )

        expected_equilibration_boundaries = pd.DataFrame(
            expected_boundaries,
            columns=["start_time", "end_time"],
            dtype="datetime64[ns]",
        ).reset_index(
            drop=True
        )  # Coerce to a RangeIndex when creating empty DataFrame

        pd.testing.assert_frame_equal(
            parsed_equilibration_boundaries, expected_equilibration_boundaries
        )


class TestPivotProcessExperimentResults:
    def test_combines_image_rows_by_ROI(self):
        test_process_experiment_file_path = pkg_resources.resource_filename(
            "osmo_jupyter", "test_fixtures/test_process_experiment_result.csv"
        )
        test_process_experiment_data = pd.read_csv(
            test_process_experiment_file_path, parse_dates=["timestamp"]
        )
        pivot_results = module.pivot_process_experiment_results_on_ROI(
            experiment_df=test_process_experiment_data,
            ROI_names=list(test_process_experiment_data["ROI"].unique()),
            msorm_types=["r_msorm", "g_msorm"],
        )

        expected_results_data = (
            pd.DataFrame(
                [
                    {
                        "timestamp": pd.to_datetime("2019-01-01 00:00:00"),
                        "ROI 0 r_msorm": 0.5,
                        "ROI 1 r_msorm": 0.4,
                        "ROI 0 g_msorm": 0.4,
                        "ROI 1 g_msorm": 0.5,
                        "image": "image-0.jpeg",
                    },
                    {
                        "timestamp": pd.to_datetime("2019-01-01 00:00:02"),
                        "ROI 0 r_msorm": 0.3,
                        "ROI 1 r_msorm": 0.6,
                        "ROI 0 g_msorm": 0.6,
                        "ROI 1 g_msorm": 0.3,
                        "image": "image-1.jpeg",
                    },
                ]
            )
            .set_index("timestamp")
            .astype(pivot_results.dtypes)
        )

        pd.testing.assert_frame_equal(pivot_results, expected_results_data)


class TestGetAllExperimentImages:
    def test_returns_only_image_files(self, mocker):
        image_file_name = "image-0.jpeg"
        experiment_name = "test"

        mocker.patch("os.listdir", return_value=[image_file_name, "experiment.log"])

        experiment_images = module.get_all_experiment_images(
            local_sync_directory="", experiment_names=[experiment_name]
        )

        expected_images = pd.DataFrame(
            [{"experiment": experiment_name, "image": image_file_name}]
        )

        pd.testing.assert_frame_equal(experiment_images, expected_images)

    def test_has_correct_dtype_when_no_images_found(self, mocker):
        mocker.patch("os.listdir", return_value=[])

        experiment_images = module.get_all_experiment_images(
            local_sync_directory="", experiment_names=["test"]
        )

        pd.testing.assert_frame_equal(
            experiment_images,
            pd.DataFrame(columns=["experiment", "image"], dtype="object"),
        )


class TestFilterEquilibratedImages:
    def test_returns_only_equilibrated_images(self, test_calibration_file_path):
        test_roi_data = pd.DataFrame(
            [
                {"timestamp": pd.to_datetime("2019-01-01"), "image": "image-0.jpeg"},
                {"timestamp": pd.to_datetime("2019-01-03"), "image": "image-1.jpeg"},
            ]
        ).set_index("timestamp")

        test_equilibration_boundaries = pd.Series(
            {
                "start_time": pd.to_datetime("2019-01-02"),
                "end_time": pd.to_datetime("2019-01-04"),
            }
        )

        equilibrated_image_data = module.filter_equilibrated_images(
            equilibration_range=test_equilibration_boundaries, df=test_roi_data
        )

        expected_equilibrated_image_data = test_roi_data[1:]

        pd.testing.assert_frame_equal(
            equilibrated_image_data, expected_equilibrated_image_data
        )


class TestOpenAndCombineSourceData:
    def test_filters_all_data_to_equilibrated_states(
        self, mocker, test_calibration_file_path, test_picolog_file_path
    ):
        test_process_experiment_file_path = pkg_resources.resource_filename(
            "osmo_jupyter", "test_fixtures/test_process_experiment_result.csv"
        )
        test_files = ["image-0.jpeg", "image-1.jpeg", "experiment.log"]
        mocker.patch("os.listdir", return_value=test_files)

        experiment_name = "test"

        equilibrated_experiment_data = module.open_and_combine_and_filter_source_data(
            local_sync_directory="",
            experiment_names=[experiment_name],
            calibration_log_filepaths=[test_calibration_file_path],
            picolog_log_filepaths=[test_picolog_file_path],
            process_experiment_result_filepaths=[test_process_experiment_file_path],
            msorm_types=["r_msorm", "g_msorm"],
        )

        expected_experiment_data = pd.DataFrame(
            [
                {
                    "timestamp": pd.to_datetime("2019-01-01 00:00:02"),
                    "ROI 0 r_msorm": 0.3,
                    "ROI 1 r_msorm": 0.6,
                    "ROI 0 g_msorm": 0.6,
                    "ROI 1 g_msorm": 0.3,
                    "image": "image-1.jpeg",
                    "PicoLog temperature (C)": 40,
                    "setpoint temperature (C)": 40,
                    "experiment": experiment_name,
                }
            ]
        ).set_index("image")

        # Trim extra calibration log columns
        subset_experiment_data_to_compare = equilibrated_experiment_data[
            expected_experiment_data.columns
        ]

        pd.testing.assert_frame_equal(
            subset_experiment_data_to_compare,
            expected_experiment_data,
            check_dtype=False,
        )