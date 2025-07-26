import pandas as pd
from os.path import join as pjoin


def modularize(path, fname, dfNewPlant, orders, scalars_dict):
    print("Modularizing accounts")

    # Check if mass manufacturing mode is enabled
    mass_mfg_enabled = scalars_dict.get("Enable Mass Manufacturing", False)

    if mass_mfg_enabled:
        print("Mass manufacturing mode enabled - applying enhanced factory assembly")

        # Get mass manufacturing parameters
        production_volume = scalars_dict.get("Production Volume", orders)
        degree_factory = scalars_dict.get("Degree of Factory Assembly", 0.95)
        factory_setup_cost = scalars_dict.get("Factory Setup Cost", 0)
        mass_mfg_efficiency = scalars_dict.get("Mass Mfg Efficiency", 2.5)

        # Apply mass manufacturing to ALL accounts (not just modular ones)
        print(f"Applying {degree_factory*100:.1f}% factory assembly to all accounts")

        idx_modules = dfNewPlant.index.str.match(".*")  # All accounts
        labor_savings = 0

        for account in dfNewPlant.index:
            # Move material costs to factory
            dfNewPlant.loc[account, "Factory Equipment Cost"] += dfNewPlant.loc[account, "Site Material Cost"]

            # Move specified fraction of labor to factory with efficiency gain
            labor_to_factory = degree_factory * dfNewPlant.loc[account, "Site Labor Cost"]
            dfNewPlant.loc[account, "Factory Equipment Cost"] += labor_to_factory / mass_mfg_efficiency
            dfNewPlant.loc[account, "Site Labor Cost"] *= (1 - degree_factory)

            # Calculate labor savings
            labor_savings += dfNewPlant.loc[account, "Site Labor Hours"] * degree_factory
            dfNewPlant.loc[account, "Site Labor Hours"] *= (1 - degree_factory)

            # Zero out site material costs
            dfNewPlant.loc[account, "Site Material Cost"] = 0

            # Add transportation costs
            dfNewPlant.loc[account, "Factory Equipment Cost"] *= 1.02

        # Add factory setup cost to first account only
        first_account = dfNewPlant.index[0]
        dfNewPlant.loc[first_account, "Factory Equipment Cost"] += factory_setup_cost / production_volume

        print(f"Labor savings: {labor_savings:.0f} hours")
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

