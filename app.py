"""
UIDAI Aadhaar Data Dashboard - Flask Backend

This application:
1. Reads Aadhaar CSV data from selected subfolders.
2. Cleans and standardizes state and date fields.
3. Generates summary tables and plots:
   - Date-wise (monthly trends)
   - State-wise (geographical comparison)
4. Serves results through Flask to an HTML frontend.
"""

from flask import Flask, render_template,request
import pandas as pd
import numpy as np
import os
import matplotlib

# Use non-GUI backend since Flask runs without display server
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# -------------------------------------------------------------
# Directory Configuration
# -------------------------------------------------------------

# Base project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folder containing all dataset subfolders
D_FOLDER = os.path.join(BASE_DIR,"data")

# Folder where generated plots will be stored
PLOT_FOLDER = os.path.join(BASE_DIR, "static", "plots")

# Ensure plot directory exists
os.makedirs(PLOT_FOLDER, exist_ok=True)

# -------------------------------------------------------------
# State Name Correction Dictionary
# Fixes spelling variations and alternate names
# -------------------------------------------------------------

st_corr={'andaman':'andaman and nicobar island',
        'nicobar islands':'andaman and nicobar island',
        'dadra':'dadra and nagar haveli',
        'the dadra':'dadra and nagar haveli',
        'nagar haveli':'dadra and nagar haveli',
        'daman':'daman and diu',
        'diu':'daman and diu',
        'jammu':'jammu and kashmir',
        'kashmir':'jammu and kashmir',
        'orissa':'odisha',
        'pondicherry':'puducherry',
        'west  bengal':'west bengal',
        'west bangal':'west bengal',
        'westbengal':'west bengal',
        'tamilnadu':'tamil nadu',
        'uttaranchal':'uttarakhand',
        'chhatisgarh':'chhattisgarh',
        'west bengli':'west bengal',
        'jaipur':'rajasthan',
        'darbhanga':'bihar',
        'puttenhalli':'karnataka',
        'raja annamalai puram':'tamil nadu',
        'nagpur':'maharashtra',
        'madanapalle':'andhra pradesh',
        'balanagar':'telangana'}

# -------------------------------------------------------------
# Function: create()
# Reads all CSV files from selected dataset folder
# Performs cleaning and preprocessing
# -------------------------------------------------------------

def create(selected_folder):

    dataframes = []

    # Collect all CSV files inside chosen subfolder
    folder_path = os.path.join(D_FOLDER, selected_folder)
    csv_files = [f for f in os.listdir(folder_path) if f.endswith(".csv")]

    # Read each CSV and append to list
    for file in csv_files:
        path = os.path.join(folder_path, file)
        df = pd.read_csv(path)
        dataframes.append(df)
    
    # Merge all CSVs into one DataFrame
    df = pd.concat(dataframes, ignore_index=True)

    # ---------------------------------------------------------
    # Data Cleaning
    # ---------------------------------------------------------

    # Convert state names to lowercase
    df.state=df.state.str.lower()

    # Replace separators with comma, then split multiple states
    df['state'] = df['state'].str.replace('&', ',', regex=False)
    df['state'] = df['state'].str.replace(' and ', ',', regex=False)
    df['state'] = df['state'].str.replace('/', ',', regex=False)
    df['state'] = df['state'].str.split(',')

    # Expand rows having multiple states
    df = df.explode('state')

    # Trim spaces
    df.state=df.state.str.strip()

    df=df[df['state']!='100000']
    df.reset_index(drop=True, inplace=True)

    # Apply correction mapping
    df['state']=df['state'].replace(st_corr)

    # Convert date column to datetime format
    df['date']=pd.to_datetime(df['date'],format='%d-%m-%Y')

    return df

# -------------------------------------------------------------

def enrol_date_wise(df,stv=''):

    df['month']=df['date'].dt.to_period('M')
    mt=df.groupby(["month", "state"], as_index=False)[["age_0_5", "age_5_17", "age_18_greater",'total']].sum()

    c1=0
    if stv!='':
        dts=mt[mt['state']==stv].groupby('month',as_index=False).agg({'age_0_5':'sum','age_5_17':'sum','age_18_greater':'sum','total':'sum'})
        s_name=stv.replace(" ","-")
        filename=f"date_plot_{s_name}.png"
    else:
        dts=mt.groupby('month',as_index=False).agg({'age_0_5':'sum','age_5_17':'sum','age_18_greater':'sum','total':'sum'})
        filename="date_plot.png"
    
    dts['c_age_0_5']=c1+pd.Series(dts['age_0_5']).cumsum()
    dts['c_age_5_17']=c1+pd.Series(dts['age_5_17']).cumsum()
    dts['c_age_18_greater']=c1+pd.Series(dts['age_18_greater']).cumsum()
    dts['c_total']=dts['c_age_0_5']+dts['c_age_5_17']+dts['c_age_18_greater']
    
    dx=dts["month"].dt.to_timestamp()
    dy1=dts.age_0_5
    dy2=dts.age_5_17
    dy3=dts.age_18_greater
    dy4=dts.total
    dy5=dts.c_age_0_5
    dy6=dts.c_age_5_17
    dy7=dts.c_age_18_greater
    dy8=dts.c_total

    fig,ax1=plt.subplots(figsize=(10,6))

    w=0.4
    x=range(len(dx))

    ax1.bar([i - w*(3/4) for i in x],dy1,width=w/2,label="0-5",alpha=0.8,color='#264653')
    ax1.bar([i - w/4 for i in x],dy2,width=w/2,label="5-17",alpha=0.8,color='#2a9d8f')
    ax1.bar([i + w/4 for i in x],dy3,width=w/2,label="18+",alpha=0.8,color='#e9c46a')
    ax1.bar([i + w*(3/4) for i in x],dy4,width=w/2,label='total',alpha=0.8,color='#f4a261')

    ax1.grid(axis='y',linestyle='--',alpha=0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(dx.dt.strftime('%b-%Y'), rotation=45)

    ax2=ax1.twinx()
    ax2.plot([i for i in x],dy5,label="0-5(Cummulative)",linewidth=2,linestyle='-',marker='o',markeredgecolor="black",markeredgewidth=1.2,color='#264653')
    ax2.plot([i for i in x],dy6,label="5-17(Cummulative)",linewidth=2,linestyle='-',marker='o',markeredgecolor="black",markeredgewidth=1.2,color='#2a9d8f')
    ax2.plot([i for i in x],dy7,label="18+(Cummulative)",linewidth=2,linestyle='-',marker='o',markeredgecolor="black",markeredgewidth=1.2,color='#e9c46a')
    ax2.plot([i for i in x],dy8,label='total(Cummulative)',linewidth=2,linestyle='-',marker='o',markeredgecolor="black",markeredgewidth=1.2,color='#f4a261')

    ax1.legend(loc="upper left")

    if stv!='':
        plt.title(f'{stv.title()}')
    else:
        plt.title('India')
    ax1.set_xlabel("Period")
    ax1.set_ylabel("Number of Adhaar enrolled")
    ax2.set_ylabel("Cummulative number of Adhaar")

    plt.tight_layout()

    date_plot_path = os.path.join(PLOT_FOLDER, filename)
    plt.savefig(date_plot_path)
    plt.close()

    dts=dts[['month','age_0_5','age_5_17','age_18_greater','total']]
    return dts, f"plots/{filename}"

# -------------------------------------------------------------

def enrol_state_wise(df, s='',e=''):

    s=pd.to_datetime(s) if s!='' else df.date.min()
    e=pd.to_datetime(e) if e!='' else df.date.max()

    sts=df.groupby('state',as_index=False).agg({'age_0_5':'sum','age_5_17':'sum','age_18_greater':'sum','total':'sum'})

    if s>df.date.min() or e<df.date.max():
        sts=df[df['date'].between(s,e)].groupby('state',as_index=False).agg({'age_0_5':'sum','age_5_17':'sum','age_18_greater':'sum','total':'sum'})
    
    sx=sts.state
    sy1=sts.age_0_5
    sy2=sts.age_5_17
    sy3=sts.age_18_greater

    w,x=0.4,np.arange(len(sx))

    plt.figure()
    plt.bar(x-w*(2/3),sy1,width=w*(2/3),label="0-5",color='#2a9d8f')
    plt.bar(x,sy2,width=w*(2/3),label="5-17",color='#e9c46a')
    plt.bar(x+w*(2/3),sy3,width=w*(2/3),label="18+",color='#f4a261')
    plt.xticks(x,sx,fontsize=8,rotation=75)
    plt.title('state-wise')
    plt.legend()

    plt.tight_layout()

    if s==df.date.min() and e==df.date.max():
        filename="state_plot.png"
    else:
        filename="temp_state_plot.png"
    state_plot_path = os.path.join(PLOT_FOLDER, filename)
    plt.savefig(state_plot_path)
    plt.close()

    return sts, f"plots/{filename}"

# -------------------------------------------------------------

def bio_date_wise(df,stv=''):

    df['month']=df['date'].dt.to_period('M')
    mt=df.groupby(["month", "state"], as_index=False)[["bio_age_5_17", "bio_age_17_",'total']].sum()

    c1=0

    if stv!='':
        dts=mt[mt['state']==stv].groupby('month',as_index=False).agg({'bio_age_5_17':'sum','bio_age_17_':'sum','total':'sum'})
        s_name=stv.replace(" ","-")
        filename=f"date_plot_{s_name}.png"
    else:
        dts=mt.groupby('month',as_index=False).agg({'bio_age_5_17':'sum','bio_age_17_':'sum','total':'sum'})
        filename="date_plot.png"
    
    dts['c_bio_age_5_17']=c1+pd.Series(dts['bio_age_5_17']).cumsum()
    dts['c_bio_age_17_']=c1+pd.Series(dts['bio_age_17_']).cumsum()
    dts['c_total']=dts['c_bio_age_5_17']+dts['c_bio_age_17_']
    
    dx=dts["month"].dt.to_timestamp()
    dy1=dts.bio_age_5_17
    dy2=dts.bio_age_17_
    dy3=dts.total
    dy4=dts.c_bio_age_5_17
    dy5=dts.c_bio_age_17_
    dy6=dts.c_total

    fig,ax1=plt.subplots(figsize=(10,6))

    w=0.4
    x=range(len(dx))

    ax1.bar([i - w*(2/3) for i in x],dy1,width=w*(2/3),label="5-17",alpha=0.8,color='#2a9d8f')
    ax1.bar([i for i in x],dy2,width=w*(2/3),label="17+",alpha=0.8,color='#e9c46a')
    ax1.bar([i + w*(2/3) for i in x],dy3,width=w*(2/3),label='total',alpha=0.8,color='#f4a261')

    ax1.grid(axis='y',linestyle='--',alpha=0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(dx.dt.strftime('%b-%Y'), rotation=45)

    ax2=ax1.twinx()
    ax2.plot([i for i in x],dy4,label="5-17(Cummulative)",color='#2a9d8f',linewidth=2,linestyle='-',marker='o',markeredgecolor="black",markeredgewidth=1.2)
    ax2.plot([i for i in x],dy5,label="17+(Cummulative)",color='#e9c46a',linewidth=2,linestyle='-',marker='o',markeredgecolor="black",markeredgewidth=1.2)
    ax2.plot([i for i in x],dy6,label='total(Cummulative)',color='#f4a261',linewidth=2,linestyle='-',marker='o',markeredgecolor="black",markeredgewidth=1.2)

    ax1.legend(loc="upper left")

    if stv!='':
        plt.title(f'{stv.title()}')
    else:
        plt.title('India')
    ax1.set_xlabel("Period")
    ax1.set_ylabel("Number of Adhaar enrolled")
    ax2.set_ylabel("Cummulative number of Adhaar")

    plt.tight_layout()

    date_plot_path = os.path.join(PLOT_FOLDER, filename)
    plt.savefig(date_plot_path)
    plt.close()

    dts=dts[['month','bio_age_5_17','bio_age_17_','total']]
    return dts, f"plots/{filename}"

# -------------------------------------------------------------

def bio_state_wise(df,s='',e=''):

    s=pd.to_datetime(s) if s!='' else df.date.min()
    e=pd.to_datetime(e) if e!='' else df.date.max()

    sts=df.groupby('state',as_index=False).agg({'bio_age_5_17':'sum','bio_age_17_':'sum','total':'sum'})

    if s>df.date.min() or e<df.date.max():
        sts=df[df['date'].between(s,e)].groupby('state',as_index=False).agg({'bio_age_5_17':'sum','bio_age_17_':'sum','total':'sum'})
    
    sx=sts.state
    sy2=sts.bio_age_5_17
    sy3=sts.bio_age_17_

    w,x=0.4,np.arange(len(sx))

    plt.bar(x-w/2,sy2,width=w,label="5-17",color='#264653')
    plt.bar(x+w/2,sy3,width=w,label="18+",color='#2a9d8f')
    plt.xticks(x,sx,fontsize=8,rotation=75)
    plt.title('state-wise')
    plt.legend()

    plt.tight_layout()

    if s==df.date.min() and e==df.date.max():
        filename="state_plot.png"
    else:
        filename="temp_state_plot.png"
    state_plot_path = os.path.join(PLOT_FOLDER, filename)
    plt.savefig(state_plot_path)
    plt.close()

    return sts, f"plots/{filename}"

# -------------------------------------------------------------

def demo_date_wise(df,stv=''):

    df['month']=df['date'].dt.to_period('M')
    mt=df.groupby(["month", "state"], as_index=False)[["demo_age_5_17", "demo_age_17_",'total']].sum()

    c1=0

    if stv!='':
        dts=mt[mt['state']==stv].groupby('month',as_index=False).agg({'demo_age_5_17':'sum','demo_age_17_':'sum','total':'sum'})
        s_name=stv.replace(" ","-")
        filename=f"date_plot_{s_name}.png"
    else:
        dts=mt.groupby('month',as_index=False).agg({'demo_age_5_17':'sum','demo_age_17_':'sum','total':'sum'})
        filename="date_plot.png"
    
    dts['c_demo_age_5_17']=c1+pd.Series(dts['demo_age_5_17']).cumsum()
    dts['c_demo_age_17_']=c1+pd.Series(dts['demo_age_17_']).cumsum()
    dts['c_total']=dts['c_demo_age_5_17']+dts['c_demo_age_17_']
    
    dx=dts["month"].dt.to_timestamp()
    dy1=dts.demo_age_5_17
    dy2=dts.demo_age_17_
    dy3=dts.total
    dy4=dts.c_demo_age_5_17
    dy5=dts.c_demo_age_17_
    dy6=dts.c_total

    fig,ax1=plt.subplots(figsize=(10,6))

    w=0.4
    x=range(len(dx))

    ax1.bar([i - w*(2/3) for i in x],dy1,width=w*(2/3),label="5-17",color='#2a9d8f',alpha=0.8)
    ax1.bar([i for i in x],dy2,width=w*(2/3),label="17+",color='#e9c46a',alpha=0.8)
    ax1.bar([i + w*(2/3) for i in x],dy3,width=w*(2/3),label='total',color='#f4a261',alpha=0.8)

    ax1.grid(axis='y',linestyle='--',alpha=0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(dx.dt.strftime('%b-%Y'), rotation=45)

    ax2=ax1.twinx()
    ax2.plot([i for i in x],dy4,label="5-17(Cummulative)",linewidth=2,linestyle='-',marker='o',color='#2a9d8f',markeredgecolor="black",markeredgewidth=1.2)
    ax2.plot([i for i in x],dy5,label="17+(Cummulative)",linewidth=2,linestyle='-',marker='o',color='#e9c46a',markeredgecolor="black",markeredgewidth=1.2)
    ax2.plot([i for i in x],dy6,label='total(Cummulative)',linewidth=2,linestyle='-',marker='o',color='#f4a261',markeredgecolor="black",markeredgewidth=1.2)

    ax1.set_xlabel("Period")
    ax1.set_ylabel("Number of Adhaar enrolled")
    ax2.set_ylabel("Cummulative number of Adhaar")

    ax1.legend(loc="upper left")

    if stv!='':
        plt.title(f'{stv.title()}')
    else:
        plt.title('India')
    ax1.set_xlabel("Period")
    ax1.set_ylabel("Number of Adhaar enrolled")
    ax2.set_ylabel("Cummulative number of Adhaar")

    plt.tight_layout()

    date_plot_path = os.path.join(PLOT_FOLDER, filename)
    plt.savefig(date_plot_path)
    plt.close()

    dts=dts[['month','demo_age_5_17','demo_age_17_','total']]
    return dts, f"plots/{filename}"

# -------------------------------------------------------------

def demo_state_wise(df,s='',e=''):
    
    s=pd.to_datetime(s) if s!='' else df.date.min()
    e=pd.to_datetime(e) if e!='' else df.date.max()

    sts=df.groupby('state',as_index=False).agg({'demo_age_5_17':'sum','demo_age_17_':'sum','total':'sum'})

    if s>df.date.min() or e<df.date.max():
        sts=df[df['date'].between(s,e)].groupby('state',as_index=False).agg({'demo_age_5_17':'sum','demo_age_17_':'sum','total':'sum'})
    
    sx=sts.state
    sy2=sts.demo_age_5_17
    sy3=sts.demo_age_17_

    w,x=0.4,np.arange(len(sx))

    plt.bar(x-w/2,sy2,width=w,label="5-17",color='#264653')
    plt.bar(x+w/2,sy3,width=w,label="18+",color='#2a9d8f')
    plt.xticks(x,sx,fontsize=8,rotation=75)
    plt.title('state-wise')
    plt.legend()

    plt.tight_layout()

    if s==df.date.min() and e==df.date.max():
        filename="state_plot.png"
    else:
        filename="temp_state_plot.png"
    state_plot_path = os.path.join(PLOT_FOLDER, filename)
    plt.savefig(state_plot_path)
    plt.close()

    return sts, f"plots/{filename}"

# -------------------------------------------------------------
# Dispatcher: date_wise()
# Chooses correct dataset-specific function for date analysis
# -------------------------------------------------------------

def date_wise(selected_folder,df,stv=''):

    if selected_folder=='api_data_aadhar_enrolment':

        df['total']=df['age_0_5']+df['age_5_17']+df['age_18_greater']
        return enrol_date_wise(df, stv)
    
    elif selected_folder=='api_data_aadhar_biometric':

        df['total']=df['bio_age_5_17']+df['bio_age_17_']
        return bio_date_wise(df, stv)
    
    elif selected_folder=='api_data_aadhar_demographic':

        df['total']=df['demo_age_5_17']+df['demo_age_17_']
        return demo_date_wise(df, stv)

# -------------------------------------------------------------
# Dispatcher: state_wise()
# Chooses correct dataset-specific function for state analysis
# -------------------------------------------------------------

def state_wise(selected_folder,df,s='',e=''):

    if selected_folder=='api_data_aadhar_enrolment':

        df['total']=df['age_0_5']+df['age_5_17']+df['age_18_greater']
        return enrol_state_wise(df, s, e)
    
    elif selected_folder=='api_data_aadhar_biometric':

        df['total']=df['bio_age_5_17']+df['bio_age_17_']
        return bio_state_wise(df, s, e)
    
    elif selected_folder=='api_data_aadhar_demographic':

        df['total']=df['demo_age_5_17']+df['demo_age_17_']
        return demo_state_wise(df, s, e)

# -------------------------------------------------------------
# Flask Route: Home Page
# Handles form input and calls analysis functions
# -------------------------------------------------------------

@app.route("/",methods=["GET","POST"])
def index():

    # List available dataset subfolders
    subfolders = [f for f in os.listdir(D_FOLDER) if os.path.isdir(os.path.join(D_FOLDER, f))]

    # Initialize variables passed to template
    selected_folder = None
    date_table = state_table = None
    date_plot = state_plot = None
    states = []
    min_date = None
    max_date = None
    view_type="date"

    if request.method == "POST":

        # Folder chosen by user
        selected_folder = request.form.get("datafolder","")

        # Either 'date' or 'state'
        view_type = request.form.get("view_type","date")

        # Button action type
        action=request.form.get("action","load")

        # Build dataframe
        df = create(selected_folder)

        # Populate dropdown filters
        states = sorted(df['state'].unique())
        min_date = df['date'].min().strftime('%Y-%m-%d')
        max_date = df['date'].max().strftime('%Y-%m-%d')

        # Generate outputs only if user clicks "Generate"
        if action == "generate":

            # ---- DATE WISE ----
            if view_type == "date":

                stv = request.form.get("state_filter","")  # '' means all
                date_summary, date_plot = date_wise(selected_folder,df, stv)
                date_table = date_summary.to_html(index=False)

            # ---- STATE WISE ----
            elif view_type == "state":

                s = request.form.get("start_date","")
                e = request.form.get("end_date","")
                state_summary, state_plot = state_wise(selected_folder,df, s, e)
                state_table = state_summary.to_html(index=False)

    # Render frontend template
    return render_template("index.html",
                           subfolders=subfolders,
                           selected_folder=selected_folder,
                           date_table=date_table,
                           state_table=state_table,
                           date_plot=date_plot,
                           state_plot=state_plot,
                           states=states,
                           min_date=min_date,
                           max_date=max_date,
                           view_type=view_type)

# -------------------------------------------------------------
# Run Flask Development Server
# -------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
