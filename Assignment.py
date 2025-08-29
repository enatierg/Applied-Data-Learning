#!/usr/bin/env python
# coding: utf-8

# ## Exposure rating model for UAVs
# 
# The algorithm below can be used to calculate premiums for drones, and cameras which can be detached and attached to different drones. The calculations of premiums are based on the ones given in the Excel file. 

# In[20]:


import pandas as pd
import numpy as np
import math


# A function to calculate Riebesell ILF is given below. 
# 
# Formula: $ILF(x*base) = x^a$, where $1 > a > 0$.
# 
# Retrived from: "Distributions Underlying Power Function ILF’s
# (Riebesell Revisited)" by Gary G Venter, John Pagliaccio.

# In[21]:


def riebesell(limit):
    baselimit = 1000000
    z = 0.2
    alpha = math.log2(1+z)
    # boundary handling for negative limit values
    if limit<=0:
       return 0.0
    ilf = (limit/baselimit)**alpha
    return ilf


# In[22]:


 # creating a class for all the data and calculations for the UAVs rating model portfolio.
class portfolio:
    # input data:
    def __init__(self, insured, underwriter, broker, brokerage):
        self.insured = insured
        self.underwriter = underwriter
        self.broker = broker
        self.brokerage = brokerage
        # defining the input data types
        dtypes = {"serialnumber": str,"valuegbp": float, "weightband": str,"hasdetachablecamera": bool,"tpllimit": float, "tplexcess": float,
                  "assettype": str,"hullpremium": float, "tpllayerpremium": float,"premium": float,
                  "rate": float, "baserate": float,"weightmultiplier": float, "finalrate": float, "tplbaserate": float,
                  "tplbaselayerpremium": float, "tplilf": float,"totalprem": float}
        self.df = pd.DataFrame(columns=dtypes.keys()).astype(dtypes)

    def dataframe(self,data,assettype):
        dfnew = pd.DataFrame(data) 
        dfnew["assettype"] = assettype
        self.df = pd.concat([self.df,dfnew],ignore_index=True)
        # filling NAs with 0.0. 
        self.df.fillna(0.0, inplace=True) 

    # calculations:
    def premcalculation(self):
        # drone premium calculations:
        # creating a copy of the original df
        dronesdf = self.df[self.df["assettype"] == "drone"].copy() 
        # defining the constant parameters
        weightmult = {"0 - 5kg": 1.00,
                      "5 - 10kg": 1.20,
                      "10 - 20kg":1.60,
                      "> 20kg": 2.50}  # table of rate adjustments for different drone weight classes
        basehull = 0.06                # hull base rate
        basetpl = 0.02                 # tpl base rate

        # mapping the rate adjustments to the drones based on their weight band. we make an assumption here that if no weight is specified, the maximum 
        # weight-based rate will be automatically assigned
        dronesdf["weightmultiplier"] = dronesdf["weightband"].map(weightmult).fillna(2.5)
        dronesdf["baserate"] = basehull
        # finalhullrate=baserate*weightadjustments
        dronesdf["finalrate"] = dronesdf["baserate"]*dronesdf["weightmultiplier"]
        # hullnetpremium=finalrate*value
        dronesdf["hullpremium"] = dronesdf["valuegbp"]*dronesdf["finalrate"]

        dronesdf["tplbaserate"] = basetpl
        # baselayerpremium=tplbase*value
        dronesdf["tplbaselayerpremium"] = basetpl*dronesdf["valuegbp"]
        #ilf=riesebell(tpllimit+tplexcess)-riesebell(tplexcess)
        dronesdf["tplilf"]= np.maximum(0.0, np.minimum((dronesdf["tpllimit"]+dronesdf["tplexcess"]).apply(riebesell)-dronesdf["tplexcess"].apply(riebesell),1.0))
        dronesdf["tpllayerpremium"] =dronesdf["tplbaselayerpremium"]*dronesdf["tplilf"]

        # camera premium calculations:
        camerasdf=self.df[self.df["assettype"]=="camera"].copy()
        # max rate is determined based on the highest final rate among drones that have detachable cameras.
        maxrate=dronesdf[dronesdf["hasdetachablecamera"]]["finalrate"].max() if not dronesdf[dronesdf["hasdetachablecamera"]].empty else 0
        camerasdf["rate"]=maxrate
        camerasdf["premium"] =camerasdf["valuegbp"]*camerasdf["rate"]

        # updating the main df
        self.df.update(dronesdf)
        self.df.update(camerasdf)

    # creating the "premium summary" of the results.
    def summaries(self):
        # calcualating cumulative net and gross premiums
        hulltotnet = self.df[self.df["assettype"]=="drone"]["hullpremium"].sum()
        tpltotnet = self.df[self.df["assettype"]=="drone"]["tpllayerpremium"].sum()
        camtotnet = self.df[self.df["assettype"]=="camera"]["premium"].sum()
        # gross=net/(1-brokerage)
        tpltotgross = tpltotnet/(1-self.brokerage)
        hulltotgross = hulltotnet/(1-self.brokerage)
        camtotgross = camtotnet/(1-self.brokerage)
        self.summary = {
            "Drone Hull": {"net": hulltotnet, "gross":hulltotgross},
            "Drone TPL": {"net": tpltotnet, "gross": tpltotgross},
            "Camera Hull": {"net": camtotnet, "gross": camtotgross},
            "Total": {"net": 0, "gross": 0}}
        self.summary["Total"]["net"]=sum(v["net"] for k,v in self.summary.items() if k!="Total")
        self.summary["Total"]["gross"]=sum(v["gross"] for k,v in self.summary.items() if k!="Total")


    # formatting the results.
    def __repr__(self):
        self.summaries()
        out = []
        # portfolio details bit:
        out.append("Portfolio Details:")
        out.append("-----------------------------------------")
        out.append(f"{"Insured":<15}{self.insured}")
        out.append(f"{"Underwriter":<15}{self.underwriter}")
        out.append(f"{"Broker":<15}{self.broker}")
        out.append(f"{"Brokerage":<15}{self.brokerage:.0%}")
        out.append("-----------------------------------------")

        # drone information bit:
        out.append("\nDrone Information:")
        droneinfo = self.df[self.df["assettype"] == "drone"][["serialnumber", "valuegbp", "weightband", "hasdetachablecamera", "tpllimit", "tplexcess"]].copy()

        # formatting the column names and data formats
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

        # hull calculations bit:
        out.append("\nHull Calculations:")
        # including the required intermediate values and ensuring correct column names and data formats
        hullcalc = self.df[self.df["assettype"] == "drone"][["serialnumber", "baserate", "weightmultiplier", "finalrate", "hullpremium"]].copy()
        hullcalc = hullcalc.rename(columns={"serialnumber": "Serial Number", 
                                            "baserate": "Hull Base",            
                                            "weightmultiplier": "Weight adjustment",
                                            "finalrate": "Hull Final Rate",
                                            "hullpremium": "Hull Premium"})
        hullcalc["Hull Base"] = hullcalc["Hull Base"].apply(lambda x: f"{x:.1%}")
        hullcalc["Weight adjustment"] = hullcalc["Weight adjustment"].apply(lambda x: f"{x:.2f}")
        hullcalc["Hull Final Rate"] = hullcalc["Hull Final Rate"].apply(lambda x: f"{x:.1%}")
        hullcalc["Hull Premium"] = hullcalc["Hull Premium"].apply(lambda x: f"{x:,.0f}")
        out.append(hullcalc.to_string())

        # tpl calculations bit:
        out.append("\nTPL Calculations:")
        # including the required intermediate values and ensuring correct column names and data formats
        tplsummary = self.df[self.df["assettype"] =="drone"][["serialnumber", "tplbaserate", "tplbaselayerpremium", "tplilf", "tpllayerpremium"]].copy()
        tplsummary = tplsummary.rename(columns={"serialnumber": "Serial Number",
                                                "tplbaserate": "TPL Base",
                                                "tplbaselayerpremium": "TPL Base Premium",
                                                "tplilf": "ILF",
                                                "tpllayerpremium": "TPL Premium"})
        tplsummary["TPL Base"] = tplsummary["TPL Base"].apply(lambda x: f"{x:.1%}")
        tplsummary["TPL Base Premium"] = tplsummary["TPL Base Premium"].apply(lambda x: f"{x:,.0f}")
        tplsummary["ILF"] = tplsummary["ILF"].apply(lambda x: f"{x:.2f}")
        tplsummary["TPL Premium"] =tplsummary["TPL Premium"].apply(lambda x: f"{x:,.0f}")
        out.append(tplsummary.to_string())

        # camera information bit:
        out.append("\nDetachable Cameras:")
        cameracalcssummary = self.df[self.df["assettype"] == "camera"][["serialnumber", "valuegbp", "rate", "premium"]].copy()
        cameracalcssummary = cameracalcssummary.rename(columns={"serialnumber": "Serial Number", 
                                                                 "valuegbp": "Value (GBP)", 
                                                                 "rate": "Rate", 
                                                                 "premium": "Premium"})
        cameracalcssummary["Value (GBP)"] = cameracalcssummary["Value (GBP)"].apply(lambda x: f"{x:,.0f}")
        cameracalcssummary["Rate"] = cameracalcssummary["Rate"].apply(lambda x: f"{x:.1%}")
        cameracalcssummary["Premium"] = cameracalcssummary["Premium"].apply(lambda x: f"{x:,.0f}") 
        out.append(cameracalcssummary.to_string(index=False))

        # premium summary bit:
        header = ("\nPremium Summary:")
        out.append(header)
        out.append("-----------------------------------------")
        out.append(f"{"Category":<15} {"Net":<15} {"Gross":<15}")
        out.append("-----------------------------------------")
        for key, value in self.summary.items():
            out.append(f"{key:<15} {round(value["net"]):<15,} {round(value["gross"]):<15,}")
        out.append("-----------------------------------------")
        return "\n".join(out)

# execution block.
if __name__ == "__main__":
    # no input format was specified in the task, so this part has been populated with the drone and camera data from Excel file. 

    # portfolio information:
    portfolio = portfolio(insured="Drones R Us", underwriter="Michael",broker="Aon", brokerage=0.30)

    # drone and camera information:
    dronesdata = [
        {"serialnumber": "AAA-111", "valuegbp": 10000, "weightband": "0 - 5kg", "hasdetachablecamera": True, "tpllimit": 1000000, "tplexcess": 0},
        {"serialnumber": "BBB-222", "valuegbp": 12000, "weightband": "10 - 20kg", "hasdetachablecamera": False, "tpllimit": 4000000, "tplexcess": 1000000},
        {"serialnumber": "CCC-333", "valuegbp": 15000, "weightband": "5 - 10kg", "hasdetachablecamera": True, "tpllimit": 5000000, "tplexcess": 5000000},]
    portfolio.dataframe(dronesdata, "drone")
    camerasdata = [
        {"serialnumber": "ZZZ-999","valuegbp": 5000},
        {"serialnumber": "YYY-888","valuegbp": 2500},
        {"serialnumber": "XXX-777","valuegbp": 1500},
        {"serialnumber": "WWW-666","valuegbp": 2000}]
    portfolio.dataframe(camerasdata,"camera")

    # executing main calculations
    portfolio.premcalculation()

    # printing out the results
    print(portfolio)


# ### Extensions for Premium Calculation
# 
# The code below s the premium calculation code to account for the following assumptions:
# 
# * **Drones in Operation**: Customers may have a large number of drones but warrant that they will only fly a small number (n) at any one time.
#    * The **full rate** applies to the n drones with the highest calculated premiums.
#    * A **fixed base premium** of £150 is to be charged for the remaining drones.
# 
# * **Cameras on Drones**: If there are more cameras than drones, premiums are adjusted based on the risk of being in the air.
#    * The **full rate** is applied for the n cameras with the largest values.
#    * A **fixed premium** of £50 will be charged for the remaining cameras.

# In[23]:


class portfolio:
    def __init__(self, insured, underwriter, broker, brokerage, simultanousdronelimit=None):
        # added error handling:
        if not isinstance(brokerage,(float,int)) or not (0<=brokerage<1):
            raise ValueError("Brokerage should be between 0 and 1.")
        if simultanousdronelimit is not None and not (isinstance(simultanousdronelimit,int) and simultanousdronelimit>=0):
            raise ValueError("Simultaneous drone limit should be non-negative or None.")
        self.insured = insured
        self.underwriter = underwriter
        self.broker = broker
        self.brokerage = brokerage
        # added an attribute for simultaneous drone flying limit
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
        # added checker for missing input values
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
                      "> 20kg": 2.50}
        basehull = 0.06
        basetpl = 0.02
        dronesdf["weightmultiplier"] = dronesdf["weightband"].map(weightmult).fillna(2.5)
        dronesdf["baserate"] = basehull
        dronesdf["finalrate"] = dronesdf["baserate"]*dronesdf["weightmultiplier"]
        dronesdf["hullpremium"] = dronesdf["valuegbp"]*dronesdf["finalrate"]
        dronesdf["tplbaserate"] = basetpl
        dronesdf["tplbaselayerpremium"] = basetpl*dronesdf["valuegbp"]
        dronesdf["tplilf"] = np.maximum(0.0, np.minimum((dronesdf["tpllimit"] + dronesdf["tplexcess"]).apply(riebesell)-dronesdf["tplexcess"].apply(riebesell), 1.0))
        dronesdf["tpllayerpremium"] = dronesdf["tplbaselayerpremium"]*dronesdf["tplilf"]

        camerasdf = self.df[self.df["assettype"] == "camera"].copy()
        maxrate = dronesdf[dronesdf["hasdetachablecamera"]]["finalrate"].max() if not dronesdf[dronesdf["hasdetachablecamera"]].empty else 0
        camerasdf["rate"] = maxrate
        camerasdf["premium"] = camerasdf["valuegbp"]*camerasdf["rate"]

        ############### adding the requested extensions:

        dronesdf["totalprem"]=dronesdf["hullpremium"]+dronesdf["tpllayerpremium"] 
        numdrones = len(dronesdf)
        numcameras = len(camerasdf)

        dronesdf["adjusthullprem"] = dronesdf["hullpremium"]
        dronesdf["adjusttplprem"] = dronesdf["tpllayerpremium"]
        camerasdf["adjustcamprem"] = camerasdf["premium"]

        # checking the requirement: whether the number of drones exceeds n
        if n is not None and 0<=n<numdrones:
            # finding the top n drones based on total premium and adjusting the premium to 150 cumulative for the rest.
            topndrones = dronesdf.nlargest(n,"totalprem")["serialnumber"]
            istopn = dronesdf["serialnumber"].isin(topndrones)
            dronesdf.loc[~istopn, "adjusthullprem"] = 150
            dronesdf.loc[~istopn,"adjusttplprem"] = 0

        # not mandatory: checking whether n exceeds the number of drones with cameras. 
        if n is not None:    
            camlimit = max(n,len(dronesdf[dronesdf["hasdetachablecamera"]])) 
        else:
            camlimit=None

        # checking the requirement: whether number of cameras exceeds the number of drones
        if camlimit is not None and numcameras>numdrones:
            topncameras=camerasdf.nlargest(camlimit,"valuegbp")["serialnumber"]
            istopncam=camerasdf["serialnumber"].isin(topncameras)
            camerasdf.loc[~istopncam,"adjustcamprem"]=50

        # updating df
        self.df.update(dronesdf)
        self.df.update(camerasdf)

        ################################################ 

    # creating the premium summary of the results.
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

# execution block
if __name__ == "__main__":
    portfolio = portfolio(insured="Drones R Them", underwriter="Bichael", broker="Bon", brokerage=0.30, simultanousdronelimit=3)
    dronesdata = [
        { "serialnumber": "AAA-222","valuegbp": 10000, "weightband": "0 - 5kg", "hasdetachablecamera": True, "tpllimit": 1000000, "tplexcess": 0},
        {"serialnumber": "BBB-222", "valuegbp": 12000, "weightband": "10 - 20kg", "hasdetachablecamera": False, "tpllimit":4000000, "tplexcess": 1000000},
        {"serialnumber": "CCC-333", "valuegbp": 15000, "weightband":"5 - 10kg", "hasdetachablecamera": True, "tpllimit": 5000000, "tplexcess": 5000000},
        {"serialnumber": "DDD-333", "valuegbp": 16000, "weightband": "10 - 20kg", "hasdetachablecamera": True, "tpllimit": 4500000, "tplexcess": 200000},
        {"serialnumber": "EEE-333", "valuegbp": 11000, "weightband": "0 - 5kg", "hasdetachablecamera": False, "tpllimit": 7000000, "tplexcess": 5000000}]
    portfolio.dataframe(dronesdata, "drone")
    camerasdata = [{"serialnumber": "ZZZ-999", "valuegbp": 5000},
        {"serialnumber": "YYY-888", "valuegbp": 2500},
        {"serialnumber": "XXX-777", "valuegbp": 1500},
        {"serialnumber": "WWW-666", "valuegbp": 1400},
        {"serialnumber": "VVV-555", "valuegbp": 2100},
        {"serialnumber": "UUU-666", "valuegbp": 2600},
        {"serialnumber": "TTT-555", "valuegbp": 4800}]
    portfolio.dataframe(camerasdata, "camera")
    portfolio.premcalculation(n=portfolio.simultanousdronelimit)
    print(portfolio)

