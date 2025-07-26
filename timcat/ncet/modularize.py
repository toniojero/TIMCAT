import pandas as pd
from os.path import join as pjoin


def modularize(path, fname, dfNewPlant, orders, scalars_dict, plant_characteristics=None):
    print("Modularizing accounts")

    if plant_characteristics is None:
        plant_characteristics = {}

    # Check if mass manufacturing mode is enabled
    mass_mfg_enabled = scalars_dict.get("Enable Mass Manufacturing", False)

    if mass_mfg_enabled:
        print("Mass manufacturing mode enabled - applying enhanced factory assembly")

        # Get mass manufacturing parameters
        production_volume = scalars_dict.get("Production Volume", orders)
        degree_factory = scalars_dict.get("Degree of Factory Assembly", 0.95)
        factory_setup_cost = scalars_dict.get("Factory Setup Cost", 0)
        mass_mfg_efficiency = scalars_dict.get("Mass Mfg Efficiency", 2.5)

        # Define component-specific factory assembly fractions
        factory_fractions = {
            "A.21": 0.30,  # Buildings/Structures
            "A.22": 0.95,  # Reactor Equipment
            "A.23": 0.85,  # Turbine Equipment
            "A.24": 0.90,  # Electrical Equipment
            "A.25": 0.80,  # Miscellaneous Equipment
            "A.26": 0.20,  # Heat Rejection
        }

        # Check if custom factory fractions are provided in input file
        if "Factory Fractions" in plant_characteristics:
            custom_fractions = plant_characteristics["Factory Fractions"]
            if custom_fractions:
                try:
                    parsed = {
                        k.strip(): float(v)
                        for k, v in (item.split(":") for item in str(custom_fractions).split(","))
                    }
                    factory_fractions.update(parsed)
                except Exception as e:
                    print(f"Could not parse custom factory fractions: {e}")

        print("Applying component-specific factory assembly:")
        for prefix, fraction in factory_fractions.items():
            print(f"  {prefix}: {fraction*100:.0f}% factory assembly")

        # Track labor savings by category
        labor_savings_by_category = {}

        # Apply mass manufacturing to ALL accounts (not just modular ones)
        print(f"Applying {degree_factory*100:.1f}% factory assembly to all accounts")

        idx_modules = dfNewPlant.index.str.match(".*")  # All accounts
        labor_savings = 0

        for account in dfNewPlant.index:
            # Determine factory fraction based on account prefix
            degree_factory_account = scalars_dict.get("Degree of Factory Assembly", 0.95)
            for prefix, fraction in factory_fractions.items():
                if account.startswith(prefix):
                    degree_factory_account = fraction
                    break

            # Move material costs to factory
            dfNewPlant.loc[account, "Factory Equipment Cost"] += dfNewPlant.loc[account, "Site Material Cost"]

            # Move specified fraction of labor to factory with efficiency gain
            labor_to_factory = degree_factory_account * dfNewPlant.loc[account, "Site Labor Cost"]
            dfNewPlant.loc[account, "Factory Equipment Cost"] += labor_to_factory / mass_mfg_efficiency
            dfNewPlant.loc[account, "Site Labor Cost"] *= (1 - degree_factory_account)

            # Calculate labor savings and track per category
            category = account[:4]
            labor_savings += dfNewPlant.loc[account, "Site Labor Hours"] * degree_factory_account
            labor_savings_by_category.setdefault(category, 0)
            labor_savings_by_category[category] += dfNewPlant.loc[account, "Site Labor Hours"] * degree_factory_account
            dfNewPlant.loc[account, "Site Labor Hours"] *= (1 - degree_factory_account)

            # Zero out site material costs
            dfNewPlant.loc[account, "Site Material Cost"] = 0

            # Add transportation costs
            dfNewPlant.loc[account, "Factory Equipment Cost"] *= 1.02

        # Add factory setup cost to first account only
        first_account = dfNewPlant.index[0]
        dfNewPlant.loc[first_account, "Factory Equipment Cost"] += factory_setup_cost / production_volume

        print(f"Labor savings: {labor_savings:.0f} hours")
        for cat, hours in labor_savings_by_category.items():
            print(f"  {cat}: {hours:.0f} hours saved")
        print(f"Factory setup cost per unit: ${factory_setup_cost/production_volume:,.0f}")

    else:
        # Run existing modularization logic
        try:
            modules = pd.read_excel(
                pjoin(path, fname), header=0, sheet_name="Modules", index_col="Account"
            )
            accounts = modules.index
            fact_costs = (
                modules["Factory Cost (2018 USD)"].values * scalars_dict["Factory cost mult"]
            )
            offsite_work = (
                modules["Percent Offsite Work"].values * scalars_dict["Offsite work mult"]
            )
            offsite_efficiency = (
                modules["Offsite Efficiency"].values * scalars_dict["Offsite efficiency mult"]
            )

            idx_modules = dfNewPlant.index.str.match("gggg")  # Initialize as False
            labor_savings = 0

            for i, account in enumerate(accounts):
                print("Modularizing account " + account)
                idx = dfNewPlant.index.str.match(account)
                idx_spec = dfNewPlant.index == (account)

                dfNewPlant.loc[idx, "Factory Equipment Cost"] += dfNewPlant.loc[idx, "Site Material Cost"]
                dfNewPlant.loc[idx, "Factory Equipment Cost"] += (
                    offsite_work[i] / offsite_efficiency[i] * dfNewPlant.loc[idx, "Site Labor Cost"]
                )
                dfNewPlant.loc[idx, "Site Labor Cost"] *= (1 - offsite_work[i])
                labor_savings += dfNewPlant.loc[idx, "Site Labor Hours"].sum() * (1 - offsite_work[i])
                dfNewPlant.loc[idx, "Site Labor Hours"] *= (1 - offsite_work[i])
                dfNewPlant.loc[idx, "Site Material Cost"] = 0
                dfNewPlant.loc[idx, "Factory Equipment Cost"] *= 1.02
                dfNewPlant.loc[idx_spec, "Factory Equipment Cost"] += (fact_costs[i] / orders)
                idx_modules = idx_modules | idx

            print("Labor savings: " + str(labor_savings))

        except Exception as e:
            print(f"No Modules sheet found, skipping modularization: {e}")
            idx_modules = dfNewPlant.index.str.match("gggg")  # All False

    return dfNewPlant, idx_modules

