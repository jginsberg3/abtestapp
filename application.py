import pandas as pd
import numpy as np

import scipy.stats as stats
from scipy.optimize import minimize

import urllib
import base64
from textwrap import dedent

#from plotly_dash_show_app import show_app

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go



app = dash.Dash()
# for deploying to beanstalk
application = app.server


# load CSS and style elements
app.css.append_css({'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})
colors = {'good':'#b2eab8','bad':'#e54034', 'slate':'#626D71','ceramic':'#CDCDC0','latte':'#DDBC95',
          'coffee':'#B38867','avocado':'#258039','aqua blue':'#31A9B8','tomato':'#CF3721','light_latte':'#ead6bf',
         'light_ceramic':'#dcdcd2','light_avocado':'#36bb53'}



# set parameters for the prior beta distributions
alphaPrior = 1
betaPrior = 1




##### APP LAYOUT
app.layout = html.Div(children=[

    # header section
    html.Div(children=[
        html.H1('A/B Test App', style={'marginTop':'10px'}),
        html.P('See bottom of doc for insturctions on how to use this tool.  Sample data has been input below as an example.'),
        html.P('Note: this test assumes that the basic principals of A/B Testing have been followed for setting up the test correctly (reach for questions on test set-up).',style={'font-style':'italic'})
    ], style={'marginLeft':'10px','marginRight':'10px','marginTop':'10px','marginBottom':'10px'}),


    # data entry boxes
    html.Div(children=[
        # test data
        html.Div(children=[
            html.H6('Test Data', style={'textDecoration':'underline', 'fontWeight':'bold'}),
            html.P('Test Impressions'),
            html.P(dcc.Input(id='testImpressions',
                     value=100,
                     type='number',
                     min=0
                     )
            ),
            html.P('Test Conversions'),
            html.P(dcc.Input(id='testConversions',
                     value=5,
                     type='number',
                     min=0
                     )
            )

        ], style={'width':'30%', 'display':'inline-block','marginLeft':'10px','marginRight':'10px'}),
        # control data
        html.Div(children=[
            html.H6('Control Data', style={'textDecoration':'underline', 'fontWeight':'bold'}),
            html.P('Control Impressions'),
            html.P(dcc.Input(id='controlImpressions',
                     value=120,
                     type='number',
                     min=0
                     )
            ),
            html.P('Control Conversions'),
            html.P(dcc.Input(id='controlConversions',
                     value=4,
                     type='number',
                     min=0
                     )
            )
        ], style={'width':'30%', 'display':'inline-block','marginLeft':'10px','marginRight':'10px'})
    ], style={'marginBottom':'50px'}),


    # text box describing how much better Test is than Control
    html.Div(id='performanceBox', children = [], style={'marginLeft':'10px','marginRight':'10px'}),


    # chart with both conversion rates
    html.Div(children=[
        # graph showing probability distributions for two groups
        dcc.Graph(id='convRatesGraph')
    ], style={'border-style':'solid','marginLeft':'10px','marginRight':'10px'}),

    # chart with delta conversion rate
    html.Div(children=[
        # graph showing the delta probability distribution (1 graph)
        dcc.Graph(id='deltaGraph')
    ], style={'marginTop':'5px','marginBottom':'10px','border-style':'solid','marginLeft':'10px','marginRight':'10px'}),

    # desired improvement section
    html.Div(children=[
        # left hand side --> input box
        html.Div(children=[
            #html.P('Enter your desired percentage-point improvement --> TO-DO ADD MORE DETAILED INSTRUCTIONS'),
            dcc.Markdown(dedent('''
            **Enter your desired percentage-point improvement below**

            *Enter percentage-point increase (see instructions below)*
            ''')),
            dcc.Input(id='desiredImprovement',
                     value=0
                     #type='number'
                     )
        ], style={'width':'50%', 'display':'inline-block'}),

        # right hand side  --> results box
        html.Div(id='desidredImprovementText', children=[], style={'width':'50%', 'display':'inline-block'})
    ], style={'marginLeft':'10px','marginRight':'10px','marginTop':'10px','marginBottom':'100px'}),


    ### insert insturctions here
    # instructions section
    html.Div(children=[
        dcc.Markdown(dedent('''
        #### Instructions for using the A/B Test App
        **Entering Test and Control Data**
        - Enter the number of Impressions and Conversions for both the Test and Control groups.
            - Make sure Conversions are **less-than-or-equal-to** Impressions or the test will not display correctly.
            - Clicks could be substituted for Impressions for Search campaigns.
        - After you enter the impressions and conversions, the two graphs will update.
            - The first graph displays the distribution of likely true conversion rates of each group.  The text above the graph displays the probability that the Test group will deliver a higher conversion rate than the Control group.
            - The second graph displays the delta of the two groups (Test conversion rate minus Control conversion rate).  The vertical grey bar at 0 represents the point where the two groups deliver even performance.
                - Positive numbers to the right of 0 represent the probability that Test outperforms Control.  Negative numbers to the left of 0 represent probability that Test performs worse than Control.


        **Using the Desired Improvement tool**
        - In the final section below the charts, you can enter a desired improvement.  For instance, if you require that Test outperforms Control by 3.5 percentage points, you can calculate the probability of that result occuring.
        - Enter the percentage-point change you want to see (not a percent increase)
        - For instance, if Control had a Cvr Rate of 5.0% and you wanted Test to deliver at least a 7.2% Cvr Rate, that would be a percentage point change of 2.2% (7.2-5.0).
        - Enter the number as a percent without the "%" sign.
            - In the example above, you would enter "2.2" (not "0.022" or "2.2%")
        - If you wanted to see Test deliver a Cvr Rate 0.03 percentage points higher than Control (for example: 0.06% vs. 0.04%), you would enter "0.03" into the box.
        '''))
    ], style={'marginLeft':'10px','marginRight':'10px'})


], style={'backgroundColor':colors['light_ceramic']})



##### Dynamic Functions

# function to update to convRatesGraph (the Graph with conversion rates for both groups)
@app.callback(
    Output(component_id='convRatesGraph', component_property='figure'),
    [Input(component_id='testImpressions', component_property='value'),
    Input(component_id='testConversions', component_property='value'),
    Input(component_id='controlImpressions', component_property='value'),
    Input(component_id='controlConversions', component_property='value')])
def updateConvRatesGraph(tImp,tConv,cImp,cConv):
    # get updated posterior beta distributions by updating the prior distributinos with the observed data
    tPosterior = stats.beta(alphaPrior + tConv,
                            betaPrior + tImp - tConv)
    cPosterior = stats.beta(alphaPrior + cConv,
                            betaPrior + cImp - cConv)

    # get a maximum x axis value to plot
    maxX = np.append(tPosterior.ppf(0.9999), cPosterior.ppf(0.9999)).max()
    maxX = maxX * 1.2  # to show a little further than the distribution goes

    # get values for plotting
    nSamples=2000
    xPlot = np.linspace(0, maxX, nSamples)

    yT = [tPosterior.pdf(i) for i in xPlot]
    yC = [cPosterior.pdf(i) for i in xPlot]

    # set up plotly traces
    traceT = go.Scatter(
        x = xPlot,
        y = yT,
        mode='lines',
        name='Test',
        fill='tozeroy',
        line=dict(
            color=(colors['aqua blue'])
        )
    )

    traceC = go.Scatter(
        x = xPlot,
        y = yC,
        mode='lines',
        name='Control',
        fill='tozeroy',
        line=dict(
            color=(colors['tomato'])
        )
    )

    # put all traces into a list "data"
    data = [traceT, traceC]

    # set up layout
    layout = go.Layout(
        title='Conversion Rate Probability Distribution',
        yaxis= dict(
            title='Density (Likelihood of Occuring)',
            hoverformat=',.1f'
        ),
        xaxis = dict(
            title='Conversion Rate',
            tickformat='.2%',
            hoverformat='.2%'
        ),
        plot_bgcolor=colors['light_latte'],
        paper_bgcolor=colors['light_ceramic']
    )

    # return a dict with data and layout --> this will be passed into the 'figure' property of the dcc.Graph
    return {'data': data,'layout': layout}


# function to update the 'performanceBox' text describing how how much better test is than control
@app.callback(
    Output(component_id='performanceBox', component_property='children'),
    [Input(component_id='testImpressions', component_property='value'),
    Input(component_id='testConversions', component_property='value'),
    Input(component_id='controlImpressions', component_property='value'),
    Input(component_id='controlConversions', component_property='value')])
def updatePerformanceBo(tImp,tConv,cImp,cConv):
    # get updated posterior beta distributions by updating the prior distributinos with the observed data
    tPosterior = stats.beta(alphaPrior + tConv,
                            betaPrior + tImp - tConv)
    cPosterior = stats.beta(alphaPrior + cConv,
                            betaPrior + cImp - cConv)

    numSamples = 20000

    pTest = tPosterior.rvs(numSamples)
    pControl = cPosterior.rvs(numSamples)

    testBetter = (pTest > pControl).mean()

    return html.P('The Test version outperforms the Control version {:,.2f}% of the time:'.format(testBetter*100),
                 style={'fontWeight':'bold'})

# function to update the 'deltaGraph'
@app.callback(
    Output(component_id='deltaGraph', component_property='figure'),
    [Input(component_id='testImpressions', component_property='value'),
    Input(component_id='testConversions', component_property='value'),
    Input(component_id='controlImpressions', component_property='value'),
    Input(component_id='controlConversions', component_property='value')])
def updateDeltaGraph(tImp,tConv,cImp,cConv):
    # get updated posterior beta distributions by updating the prior distributinos with the observed data
    tPosterior = stats.beta(alphaPrior + tConv,
                            betaPrior + tImp - tConv)
    cPosterior = stats.beta(alphaPrior + cConv,
                            betaPrior + cImp - cConv)

    numSamples = 20000

    pTest = tPosterior.rvs(numSamples)
    pControl = cPosterior.rvs(numSamples)

    pDelta = pTest - pControl

    traceH = go.Histogram(
        x = pDelta,
        opacity=0.7,
        autobinx=False,
        nbinsx=30,
        #xbins=dict(start=min(pDelta),end=max(pDelta),size=30),
        histnorm='percent',
        name='Conversion Rate Delta',
        marker={'color':colors['light_avocado']},
        #hoverinfo = 'y'
        hoverlabel = {'namelength':-1}

    )

    zeroLine = go.Scatter(
        x = [0,0],
        y = [0,4],
        mode='lines',
        name='Even Performance',
        line={'color':'rgb(128,128,128)', 'width':4},
        text = ['Even Performance','Even Performance'],
        hoverinfo = 'text'
    )

    data = [traceH,zeroLine]

    layout = go.Layout(
        title='Delta between Test and Control Conversion Rates',
        yaxis= dict(
            title='Density (Likelihood of Occuring)'
        ),
        xaxis = dict(
            title='Conversion Rate Delta <br> <sub>Positive: Test Cvr Rate is greater than Control Cvr Rate</sub> <br> <sub>Negative: Test Cvr Rate is less than Control Cvr Rate</sub>',
            tickformat='.2%',
            hoverformat='.2%'
        ),
        plot_bgcolor=colors['light_latte'],
        paper_bgcolor=colors['light_ceramic']
    )

    return {'data':data, 'layout':layout}

# function to update the "desidredImprovementText" Div
@app.callback(
    Output(component_id='desidredImprovementText', component_property='children'),
    [Input(component_id='desiredImprovement', component_property='value')],
    [State(component_id='testImpressions', component_property='value'),
    State(component_id='testConversions', component_property='value'),
    State(component_id='controlImpressions', component_property='value'),
    State(component_id='controlConversions', component_property='value')])
def updateDesiredImprovementText(desImprov, tImp,tConv,cImp,cConv):
    # get updated posterior beta distributions by updating the prior distributinos with the observed data
    tPosterior = stats.beta(alphaPrior + tConv,
                            betaPrior + tImp - tConv)
    cPosterior = stats.beta(alphaPrior + cConv,
                            betaPrior + cImp - cConv)

    numSamples = 20000

    pTest = tPosterior.rvs(numSamples)
    pControl = cPosterior.rvs(numSamples)

    pDelta = pTest - pControl

    desImprov = float(desImprov)/100

    _improv = pDelta > desImprov
    res = _improv.sum() / len(pDelta)

    return html.P('There is a {:.1%} probability of Test delivering a conversion rate {:.2f} percentage points higher than Control'.format(
    res, desImprov*100))




if __name__ == '__main__':
  # make sure use "application" here, not "app"
  # Beanstalk expects it to be running on 8080
  application.run(host='0.0.0.0')
