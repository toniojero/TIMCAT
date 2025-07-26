import argparse
from os.path import join as pjoin, dirname
from . import cost_model


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run TIMCAT cost model")
    parser.add_argument("plant", help="Plant identifier e.g. PWR12ME")
    data_dir = pjoin(dirname(__file__), "..", "data")
    parser.add_argument(
        "--basis",
        default=pjoin(data_dir, "PWR12_ME_inflated_reduced.csv"),
        help="Basis cost CSV file",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Input Excel file. Defaults to inputfile_<plant>.xlsx",
    )
    parser.add_argument(
        "--params",
        default=pjoin(data_dir, "input_scaling_exponents.xlsx"),
        help="Scaling parameter Excel file",
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=10,
        help="Number of plant orders to simulate",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of Monte Carlo runs",
    )
    parser.add_argument(
        "--make-building-table",
        action="store_true",
        help="Generate scheduler building table",
    )
    parser.add_argument(
        "--save-all",
        action="store_true",
        help="Save all intermediate files",
    )
    args = parser.parse_args(argv)

    plant_fname = args.input or pjoin(data_dir, f"inputfile_{args.plant}.xlsx")

    cost_model.run_ncet(
        args.plant,
        cost_model.os.path.dirname(__file__),
        args.orders,
        plant_fname,
        args.params,
        args.basis,
        mc_runs=args.runs,
        make_building_table=args.make_building_table,
        save_all=args.save_all,
    )


if __name__ == "__main__":
    main()
