import pandas as pd
import numpy_financial as npf

from datetime import date


pd.core.common.is_list_like = pd.api.types.is_list_like
import pandas_datareader as web
from scipy.stats import norm
from pandas_datareader import data
from pandas.tseries.offsets import BusinessDay
from flask import Flask, render_template, request, jsonify, flash, send_file
from forms import InputForm
from config import Config
from flask_bootstrap import Bootstrap
import jinja2
from io import BytesIO


import warnings
import os
from flask import send_from_directory


from flask import Flask
app = Flask(__name__)
Bootstrap(app)
app.config.from_object(Config)

def render_search_response(gen_json:bool=False) -> str:
    IntInv = int(request.form['IntInv'])
    OpMainCosts = int(request.form['OpMainCosts'])
    OpMainGrowth = float(request.form['OpMainGrowth'])
    FuelExp = int(request.form['FuelExp'])
    ElectGen = int(request.form['ElectGen'])
    DiscRate = float(request.form['DiscRate'])
    ExpLife = int(request.form['ExpLife'])
    start_date=date.today()

        # Create an index of the payment dates
    rng = pd.date_range(start_date, periods=ExpLife, freq='AS')
    rng.name = "Period_Start"
          
    # Build up the Amortization schedule as a DataFrame
    df = pd.DataFrame(index=rng,columns=['OpMainCostsPayment', 'FuelExpense',
                                         'PVCosts', 'YearlyOutput', 'PVOutput'], dtype='float')

    # Add index by period (start at 1 not 0)
    df.reset_index(inplace=True)
    df.index += 1
    df.index.name = "Period"
    
    # Calculate OpMainCosts, Fuel Costs and Electricity Generation
        
    df["OpMainCostsPayment"]=OpMainCosts*(1+OpMainGrowth)**(df.index-1)
    df["OpMainCostsPayment20"]=df["OpMainCostsPayment"]*1.2
    

    df["FuelExpense"] = FuelExp
    df["FuelExpense20"] = FuelExp*1.2
    df["ElectGen"] = ElectGen
    
        # Calculate Discount Factors and PV of Costs and Generation
    
    df["PVCosts"] = npf.pv(rate=DiscRate, nper=df.index, pmt=0, fv=df["OpMainCostsPayment"]+ df["FuelExpense"] )
    df["PVCostsOp20"] = npf.pv(rate=DiscRate, nper=df.index, pmt=0, fv=df["OpMainCostsPayment20"]+ df["FuelExpense"] )
    df["PVCostsFuel20"] = npf.pv(rate=DiscRate, nper=df.index, pmt=0, fv=df["OpMainCostsPayment"]+ df["FuelExpense20"] )
    df["PVCostsDisc20"] = npf.pv(rate=DiscRate*1.2, nper=df.index, pmt=0, fv=df["OpMainCostsPayment"]+ df["FuelExpense"] )
    
        # Output and PV
    
    df["YearlyOutput"] =ElectGen
    df["PVOutput"]= -np.pv(rate=DiscRate, nper=df.index, pmt=0, fv=df["YearlyOutput"] )
    df["PVOutputDisc20"]= -np.pv(rate=DiscRate*1.2, nper=df.index, pmt=0, fv=df["YearlyOutput"] )

        
        # Round the values
    df = df.round(2) 

    PVGen=round(df["PVOutput"].sum(),2)
    LCOE=round((IntInv-df["PVCosts"].sum())/df["PVOutput"].sum(),2)
    LCOEOp20=round((IntInv-df["PVCostsOp20"].sum())/df["PVOutput"].sum(),2)
    LCOEFuel20=round((IntInv-df["PVCostsFuel20"].sum())/df["PVOutput"].sum(),2)
    LCOEDisc20=round((IntInv-df["PVCostsDisc20"].sum())/df["PVOutputDisc20"].sum(),2)


    if gen_json:
        return jsonify(the_IntInv = IntInv,
                       the_OpMainCosts = OpMainCosts,
                       the_OpMainGrowth = OpMainGrowth,
                       the_FuelExp = FuelExp,
                       the_ElectGen = ElectGen,
                       the_DiscRate = DiscRate,
                       the_ExpLife = ExpLife,
                       the_PVGen= PVGen,
                       the_LCOE=LCOE,
                       the_LCOEOp20=LCOEOp20,
                       the_LCOEFuel20=LCOEFuel20,
                       the_LCOEDisc20=LCOEDisc20)
    return render_template('results.html',
                               the_title='Results from LCOE Model',
                               the_IntInv = IntInv,
                               the_OpMainCosts = OpMainCosts,
                               the_OpMainGrowth = OpMainGrowth,
                               the_FuelExp = FuelExp,
                               the_ElectGen = ElectGen,
                               the_DiscRate = DiscRate,
                               the_ExpLife = ExpLife,
                               the_PVGen= PVGen,
                               the_LCOE=LCOE,
                               the_LCOEOp20=LCOEOp20,
                               the_LCOEFuel20=LCOEFuel20,
                               the_LCOEDisc20=LCOEDisc20)





@app.route('/')



@app.route('/home')
def home_page():
    """Returns the entry page to browser."""

    return render_template('home.html',
                           the_title='Welcome to the Renewable Energy Valuation Model',
                           the_url='/entry')


@app.route('/entry', methods=['GET', 'POST'])
def entry_page():
    form = InputForm()
    """Returns the entry page to browser."""
    if form.validate_on_submit():
        return flash("Inputs submitted")
    return render_template('input.html',
                           the_title='Renewable Energy Valuation Model',
                           form=form,
                           the_url='/model')

@app.route('/model', methods=['POST'])
def model():
    """Returns the results of a call to 'securities to the browser."""
    return render_search_response()




@app.route('/homejson')
def home_json_page():
    """Returns the entry page to browser."""
    return render_template('home.html',
                           the_title='Renewable Energy Valuation Model',
                           the_url='/entry')


@app.route('/entryjson')
def entry_json_page():
    """Returns the JSON entry page to browser."""
    return render_template('input.html',
                           the_title='Renewable Energy Valuation Model',
                           the_url='/modeljson')

@app.route('/modeljson', methods=['POST'])
def modeljson():
    """Returns the results of a call to 'Renewable Energy Valuation Model ' to the browser."""
    return render_search_response(True)



@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


if __name__ == '__main__':
    app.run()
