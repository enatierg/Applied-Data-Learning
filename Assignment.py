# ## A Simple Exposure rating model for UAVs
# 
# This calculates premiums for drones, and cameras which can be detached and attached to different drones. Each drone is individually priced, 
# based on its value and weight. As the cameras can be attached to any drone, they are charged at the highest rate across all of the drones to 
# which they can be attached.
# 
# Extensions to the basic pricing:
# If a customer only flies a small number of drones at any one time, the following conditions apply:
#    * The **full rate** is only applied to the n drones with the highest calculated premiums.
#    * A **fixed base premium** of £120 is to be charged for the remaining drones.
# 
# If there are more cameras than drones, premiums are adjusted based on the risk of the camera being in the air.
#    * The **full rate** is applied for the n cameras with the largest values.
#    * A **fixed premium** of £40 will be charged for the remaining cameras.

import pandas as pd
import numpy as np
import math

def riebesell(limit):
    # A function to calculate Riebesell ILF.
    # Formula: $ILF(x*base) = x^a$, where $1 > a > 0$.
    # 
    # Retrived from: "Distributions Underlying Power Function ILF’s (Riebesell Revisited)" by Gary G Venter, John Pagliaccio.
    
    baselimit = 1000000 
    z = 0.5           
    alpha = math.log2(1+z)
    # boundary handling for negative limit values
    if limit<=0:
       return 0.0
    ilf = (limit/baselimit)**alpha
    return ilf

class portfolio:
    def __init__(self, insured, underwriter, broker, brokerage, simultanousdronelimit=None):
        # Value error handling
        if not isinstance(brokerage,(float,int)) or not (0<=brokerage<1):
            raise ValueError("Brokerage should be between 0 and 1.")
        if simultanousdronelimit is not None and not (isinstance(simultanousdronelimit,int) and simultanousdronelimit>=0):
            raise ValueError("Simultaneous drone limit should be non-negative or None.")
        self.insured = insured
        self.underwriter = underwriter
        self.broker = broker
        self.brokerage = brokerage
        self.simultanousdronelimit = simultanousdronelimit
        dtypes = {
            "serialnumber": str,"valuegbp": float,"weightband": str,"hasdetachablecamera": bool,"tpllimit": float,"tplexcess": float,
            "assettype": str,"hullpremium": float,"grosshull": float,"tpllayerpremium": float,"grosstpl": float,"premium": float,
            "grosspremium": float,"rate": float,"baserate": float,"weightmultiplier": float,"finalrate": float,"tplbaserate": float,
            "tplbaselayerpremium": float,"tplilf": float,"totalprem": float, "simultanousdronelimit":float,
            "adjusthullprem": float, "adjusthullgross": float, "adjustcamprem": float, "adjustcamgross": float,
            "adjusttplprem": float, "adjusttplgross": float}
        self.df = pd.DataFrame(columns=dtypes.keys()).astype(dtypes)

    def dataframe(self,data,assettype):
        dfnew = pd.DataFrame(data) 
        dfnew["assettype"] = assettype
        # Check whether all the information necessary for calculations is provided
        requiredinfo = {"drone": ["valuegbp", "weightband", "hasdetachablecamera", "tpllimit", "tplexcess"],
                        "camera": ["valuegbp"]}
        for col in requiredinfo.get(assettype, []):
            if dfnew[col].isnull().any():
                raise ValueError(f" Missing information on '{col}' for '{assettype}'.")
        self.df = pd.concat([self.df,dfnew],ignore_index=True)

    def premcalculation(self, n=None):
        dronesdf = self.df[self.df["assettype"] == "drone"].copy()
        weightmult = {"0 - 5kg": 1.00,
                      "5 - 10kg": 1.20,
                      "10 - 20kg":1.60,
                      "> 20kg": 2.00}
        basehull = 0.06
        basetpl = 0.02
        
        dronesdf["weightmultiplier"] = dronesdf["weightband"].map(weightmult)
        dronesdf["baserate"] = basehull
        dronesdf["finalrate"] = dronesdf["baserate"]*dronesdf["weightmultiplier"]
        dronesdf["hullpremium"] = dronesdf["valuegbp"]*dronesdf["finalrate"]
        dronesdf["tplbaserate"] = basetpl
        dronesdf["tplbaselayerpremium"] = basetpl*dronesdf["valuegbp"]
        
        # ILF=Riesebell(TPL limit + TPL excess)-Riesebell(TPL Excess)
        
        dronesdf["tplilf"] = np.maximum(0.0, np.minimum((dronesdf["tpllimit"] + dronesdf["tplexcess"]).apply(riebesell)-dronesdf["tplexcess"].apply(riebesell), 1.0))
        dronesdf["tpllayerpremium"] = dronesdf["tplbaselayerpremium"]*dronesdf["tplilf"]

        camerasdf = self.df[self.df["assettype"] == "camera"].copy()
        # Find max rate across drones with camera attachment
        maxrate = dronesdf[dronesdf["hasdetachablecamera"]]["finalrate"].max() if not dronesdf[dronesdf["hasdetachablecamera"]].empty else 0
        camerasdf["rate"] = maxrate
        camerasdf["premium"] = camerasdf["valuegbp"]*camerasdf["rate"]

        dronesdf["totalprem"]=dronesdf["hullpremium"]+dronesdf["tpllayerpremium"] 
        numdrones = len(dronesdf)
        numcameras = len(camerasdf)

        # Implement the extensions:
        
        dronesdf["adjusthullprem"] = dronesdf["hullpremium"]
        dronesdf["adjusttplprem"] = dronesdf["tpllayerpremium"]
        camerasdf["adjustcamprem"] = camerasdf["premium"]
        
        if n is not None and 0<=n<numdrones:
            # Finding the top n drones based on total premium and adjusting the premium to 120 cumulative for the rest.
            topndrones = dronesdf.nlargest(n,"totalprem")["serialnumber"]
            istopn = dronesdf["serialnumber"].isin(topndrones)
            dronesdf.loc[~istopn, "adjusthullprem"] = 120
            dronesdf.loc[~istopn,"adjusttplprem"] = 0

        # Check whether is n greater than the number of drones with attachable cameras, in which case, adjust n
        if n is not None:    
            camlimit = max(n,len(dronesdf[dronesdf["hasdetachablecamera"]])) 
        else:
            camlimit=None
        if camlimit is not None and numcameras>numdrones:
            topncameras=camerasdf.nlargest(camlimit,"valuegbp")["serialnumber"]
            istopncam=camerasdf["serialnumber"].isin(topncameras)
            camerasdf.loc[~istopncam,"adjustcamprem"]=40

        # Update the original df
        self.df.update(dronesdf)
        self.df.update(camerasdf)

    # Create a summary:
    def summaries(self):
        # changing to adjusted premoum values: 
        hulltotnet = self.df[self.df["assettype"] =="drone"]["adjusthullprem"].sum()
        tpltotnet = self.df[self.df["assettype"] == "drone"]["adjusttplprem"].sum()
        camtotnet = self.df[self.df["assettype"] == "camera"]["adjustcamprem"].sum()
        hulltotgross = hulltotnet/(1-self.brokerage)
        tpltotgross = tpltotnet/(1-self.brokerage)
        camtotgross = camtotnet/(1-self.brokerage) 
        self.summary = {
            "Drone Hull": {"net": hulltotnet,"gross": hulltotgross},
            "Drone TPL": {"net": tpltotnet, "gross": tpltotgross},
            "Camera Hull": {"net": camtotnet, "gross": camtotgross},
            "Total": {"net": 0, "gross": 0}}
        self.summary["Total"]["net"] = sum(v["net"] for k,v in self.summary.items() if k!="Total")
        self.summary["Total"]["gross"]= sum(v["gross"] for k,v in self.summary.items() if k!="Total")

    def __repr__(self):
        self.summaries()
        out = []
        out.append("Portfolio Details:")
        out.append("-----------------------------------------")
        out.append(f"{"Insured":<15}{self.insured}")
        out.append(f"{"Underwriter":<15}{self.underwriter}")
        out.append(f"{"Broker":<15}{self.broker}")
        out.append(f"{"Brokerage":<15}{self.brokerage:.0%}")
        if self.simultanousdronelimit is not None:
            out.append(f"{"Drone Limit":<15}{self.simultanousdronelimit:.0f}")
        else:
            out.append(f"{"Drone Limit":<15}{self.simultanousdronelimit}")
        out.append("-----------------------------------------")

        out.append("\nDrone Information:")
        droneinfo = self.df[self.df["assettype"]=="drone"][["serialnumber", "valuegbp", "weightband", "hasdetachablecamera", "tpllimit", "tplexcess"]].copy()
        droneinfo = droneinfo.rename(columns={"serialnumber": "Serial Number", 
                                              "valuegbp": "Value (GBP)", 
                                              "weightband": "Weight Band",
                                              "hasdetachablecamera": "Detachable Camera?", 
                                              "tpllimit": "TPL Limit", 
                                              "tplexcess": "TPL Excess"})
        droneinfo["Detachable Camera?"] = droneinfo["Detachable Camera?"].astype(str)
        droneinfo["Value (GBP)"] = droneinfo["Value (GBP)"].apply(lambda x: f"{x:,.0f}")
        droneinfo["TPL Limit"] = droneinfo["TPL Limit"].apply(lambda x: f"{x:,.0f}")
        droneinfo["TPL Excess"] = droneinfo["TPL Excess"].apply(lambda x: f"{x:,.0f}")
        out.append(droneinfo.to_string())

        out.append("\nHull Calculations:")
        hullcalc = self.df[self.df["assettype"]=="drone"][["serialnumber", "baserate", "weightmultiplier","finalrate", "hullpremium","adjusthullprem"]].copy()
        hullcalc = hullcalc.rename(columns={"serialnumber": "Serial Number", 
                                            "baserate":"Hull Base", 
                                            "weightmultiplier": "Weight adjustment",
                                            "finalrate": "Hull Final Rate", 
                                            "hullpremium":"Hull Premium",
                                            "adjusthullprem":"Adjusted Hull Premium"})
        hullcalc["Hull Base"] = hullcalc["Hull Base"].apply(lambda x: f"{x:.1%}")
        hullcalc["Weight adjustment"] = hullcalc["Weight adjustment"].apply(lambda x: f"{x:.2f}")
        hullcalc["Hull Final Rate"] = hullcalc["Hull Final Rate"].apply(lambda x: f"{x:.1%}")
        hullcalc["Hull Premium"] = hullcalc["Hull Premium"].apply(lambda x: f"{x:,.0f}")
        hullcalc["Adjusted Hull Premium"] = hullcalc["Adjusted Hull Premium"].apply(lambda x: f"{x:,.0f}")
        out.append(hullcalc.to_string())

        out.append("\nTPL Calculations:")
        tplsummary = self.df[self.df["assettype"] == "drone"][["serialnumber", "tplbaserate", "tplbaselayerpremium", "tplilf", "tpllayerpremium", "adjusttplprem"]].copy()
        tplsummary = tplsummary.rename(columns={
            "serialnumber": "Serial Number", 
            "tplbaserate": "TPL Base", 
            "tplbaselayerpremium": "TPL Base Premium",
            "tplilf": "ILF", 
            "tpllayerpremium": "TPL Premium",
            "adjusttplprem": "Adjusted TPL Premium"})
        tplsummary["TPL Base"] = tplsummary["TPL Base"].apply(lambda x: f"{x:.1%}")
        tplsummary["TPL Base Premium"] = tplsummary["TPL Base Premium"].apply(lambda x: f"{x:,.0f}")
        tplsummary["ILF"] = tplsummary["ILF"].apply(lambda x: f"{x:.2f}")
        tplsummary["TPL Premium"] = tplsummary["TPL Premium"].apply(lambda x: f"{x:,.0f}")
        tplsummary["Adjusted TPL Premium"] = tplsummary["Adjusted TPL Premium"].apply(lambda x: f"{x:,.0f}")
        out.append(tplsummary.to_string())

        out.append("\nDetachable Cameras:")
        cameracalcssummary = self.df[self.df["assettype"] == "camera"][["serialnumber", "valuegbp", "rate", "premium", "adjustcamprem"]].copy()
        cameracalcssummary = cameracalcssummary.rename(columns={"serialnumber": "Serial Number", 
                                                                 "valuegbp": "Value (GBP)", 
                                                                 "rate": "Rate", 
                                                                 "premium": "Premium",
                                                                "adjustcamprem": "Adjusted Premium"})
        cameracalcssummary["Value (GBP)"] = cameracalcssummary["Value (GBP)"].apply(lambda x: f"{x:,.0f}")
        cameracalcssummary["Rate"] = cameracalcssummary["Rate"].apply(lambda x: f"{x:.1%}")
        cameracalcssummary["Premium"] = cameracalcssummary["Premium"].apply(lambda x: f"{x:,.0f}")
        cameracalcssummary["Adjusted Premium"] = cameracalcssummary["Adjusted Premium"].apply(lambda x: f"{x:,.0f}")
        out.append(cameracalcssummary.to_string(index=False))

        header = ("\nPremium Summary:")
        out.append(header)
        out.append("-----------------------------------------")
        out.append(f"{"Category":<15} {"Net":<15} {"Gross":<15}")
        out.append("-----------------------------------------")
        for key, value in self.summary.items():
            out.append(f"{key:<15} {round(value["net"]):<15,} {round(value["gross"]):<15,}")
        out.append("-----------------------------------------")
        return "\n".join(out)

# Execution block:
if __name__ == "__main__":
    portfolio = portfolio(insured="Company Name", underwriter="Underwriter Name", broker="Broker Name", brokerage=0.15, simultanousdronelimit=2)
    dronesdata = [
        {"serialnumber": "ABC-123","valuegbp": 40000, "weightband": "0 - 5kg", "hasdetachablecamera": False, "tpllimit": 1300000, "tplexcess": 12000},
        {"serialnumber": "BCD-234", "valuegbp": 51000, "weightband": "10 - 20kg", "hasdetachablecamera": False, "tpllimit":4500000, "tplexcess": 1000000},
        {"serialnumber": "CDE-345", "valuegbp": 25000, "weightband":"5 - 10kg", "hasdetachablecamera": True, "tpllimit": 5600000, "tplexcess": 5000000},
        {"serialnumber": "DEF-456", "valuegbp": 46000, "weightband": "10 - 20kg", "hasdetachablecamera": True, "tpllimit": 4500000, "tplexcess": 0},
        {"serialnumber": "EFG-567", "valuegbp": 11000, "weightband": "0 - 5kg", "hasdetachablecamera": False, "tpllimit": 7000000, "tplexcess": 5000000}]
    portfolio.dataframe(dronesdata, "drone")
    camerasdata = [{"serialnumber": "ZZZ-999", "valuegbp": 7660},
        {"serialnumber": "YXW-888", "valuegbp": 2800},
        {"serialnumber": "XWV-777", "valuegbp": 1500},
        {"serialnumber": "WVU-666", "valuegbp": 1400},
        {"serialnumber": "VUT-555", "valuegbp": 2100}]
    portfolio.dataframe(camerasdata, "camera")
    portfolio.premcalculation(n=portfolio.simultanousdronelimit)
    print(portfolio)
