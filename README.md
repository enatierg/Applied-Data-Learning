# Learning Projects in Data Analysis

This repository contains a collection of projects I completed to explore and better understand the uses of different programming and data analysis concepts.  
For each project, I have added a **preamble** to explain its purpose and what it demonstrates, so you can understand what each does and the ideas I was experimenting with.

---

## Projects

### UAVs_explore.py
**Purpose:**  
This project is a simple automation script for calculating premiums for UAVs (unmanned aerial vehicles). The main goal was not to build a production-level tool, but to **practice using Python’s data analysis stack**.

**What it does:**  
- Automates the repetitive task of calculating UAV premiums.  
- Uses **pandas** for data handling and tabular operations.  
- Leverages **numpy** for numerical computations.  
- Provides a clean and reproducible workflow compared to manual spreadsheet calculations.

**Learning Focus:**  
This project helped me gain hands-on experience with:  
- Data cleaning and transformation  
- Vectorised computations  
- Structuring small automation scripts  

---

### Marketing_Sales_Analysis.Rmd
**Purpose:**  
This project is an R Markdown analysis exploring the impact of marketing investments and other factors on sales.  
The main goal was to **practice data wrangling, regression modelling, and ROI analysis** using R.

**What it does:**  
- Loads and merges weekly and monthly datasets, performing interpolation to align time series.  
- Generates lagged variables to capture delayed effects of marketing investments.  
- Examines multicollinearity using correlation matrices and VIFs.  
- Fits linear models and Lasso regression to identify influential variables.  
- Evaluates model performance with RMSE, R², and diagnostic tests (Durbin-Watson, Ljung-Box, Shapiro-Wilk, Breusch-Pagan).  
- Calculates and visualises **ROI of marketing channels** based on model coefficients.  
- Produces reproducible tables and plots summarising findings.

**Learning Focus:**  
This project helped me gain hands-on experience with:  
- Time series manipulation and interpolation in R  
- Linear regression, Lasso, and variable selection  
- Model diagnostics and residual analysis  
- Marketing ROI calculations and data visualisation with **ggplot2**  
- Combining data wrangling, modelling, and reporting in an R Markdown workflow  

---

