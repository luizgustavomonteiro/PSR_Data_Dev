import os
import django
import sys
import numpy as np
from scipy.stats import linregress
from django.db.models import Sum
from dash import Dash, dcc, html, Input, Output, callback, ctx
import plotly.express as px
import pandas as pd
from django.db import DatabaseError
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append("C:\\Dev\\PSR_Data_Dev\\PSR_Dev")

# Set the Django settings module
try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PSR_Dev.settings")
    django.setup()
except Exception as e:
    print(f"Failed to configure Django: {e}")
    sys.exit(1)

# Import models
from myapp.models import Notifications, Regions

def get_notification_data():
    """Fetch notification data from database"""
    try:
        data = Notifications.objects.all().values(
            'notification_id', 'disease__disease_name', 'region',
            'notification_week', 'notification_year',
            'cases_confirmed'
        )
        return pd.DataFrame(data)
    except DatabaseError as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def process_data(df_data):
    """Process DataFrame to get weekly sums"""
    if df_data is None or df_data.empty:
        return None
    
    # Group by disease, year and week and sum confirmed cases
    sum_case_week = df_data.groupby(
        ['disease__disease_name', 'notification_year', 'notification_week']
    )['cases_confirmed'].sum().reset_index()
    
    # Rename columns
    sum_case_week.rename(columns={
        'disease__disease_name': 'Disease',
        'notification_year': 'Year',
        'notification_week': 'Week',
        'cases_confirmed': 'Cases'
    }, inplace=True)
    
    return sum_case_week

def create_segments(df, week_interval):
    """Create segments (joinpoints) based on week interval"""
    # Sort by year and week to ensure correct sequence
    df_sorted = df.sort_values(by=['Year', 'Week'])
    
    # Calculate number of joinpoints
    num_joinpoints = len(df_sorted) // week_interval
    
    # Create segments
    segments = [df_sorted.iloc[i * week_interval:(i + 1) * week_interval] for i in range(num_joinpoints)]
    
    # Add remaining data if any
    if len(df_sorted) % week_interval != 0:
        segments.append(df_sorted.iloc[num_joinpoints * week_interval:])
    
    return segments

def calculate_apc_segments(segments):
    """Calculate APC for each segment using linear regression"""
    results = []
    
    for i, segment in enumerate(segments):
        if len(segment) > 1:
            x = np.arange(len(segment))
            
            # Handle zero cases
            cases = segment['Cases'].values
            cases = np.where(cases == 0, 0.01, cases)  # Replace zeros with 0.01 to avoid log(0)
            y = np.log(cases)
            
            # Perform linear regression
            slope, intercept, r_value, p_value, std_err = linregress(x, y)
            apc = (np.exp(slope) - 1) * 100  # APC calculation
            
            # Important information for each segment
            start_week = segment['Week'].iloc[0]
            end_week = segment['Week'].iloc[-1]
            start_year = segment['Year'].iloc[0]
            end_year = segment['Year'].iloc[-1]
            start_cases = segment['Cases'].iloc[0]
            end_cases = segment['Cases'].iloc[-1]
            duration = end_week - start_week + 1
            
            # Create label for X axis
            week_label = f"Weeks {start_week}-{end_week}"
            
            results.append({
                'Segment': i + 1,
                'Week_Label': week_label,
                'Start_Week': start_week,
                'End_Week': end_week,
                'Start_Year': start_year,
                'End_Year': end_year,
                'Cases_Start': start_cases,
                'Cases_End': end_cases,
                'Cases_Avg': segment['Cases'].mean(),
                'Slope': slope,
                'APC': apc,
                'R_squared': r_value ** 2,
                'P_value': p_value,
                'Duration': duration
            })
    
    return pd.DataFrame(results) if results else None

def create_dash_app(df):
    """Create and configure Dash application with simplified design"""
    app = Dash(__name__, suppress_callback_exceptions=True)

    # Get unique list of diseases and years
    unique_diseases = df['Disease'].unique()
    unique_years = sorted(df['Year'].unique())

    # Simplified application layout
    app.layout = html.Div([
        #html.H1("Epidemiological Analysis", style={'textAlign': 'center', 'margin': '20px'}),
        
        # Controls at the top in line
        html.Div([
            # Year selector (moved to top)
            html.Div([
                html.Label("Select Year:", style={'font-weight': 'bold', 'marginRight': '10px'}),
                dcc.Dropdown(
                    id="year-dropdown",
                    options=[{"label": str(year), "value": year} for year in unique_years],
                    value=unique_years[0],
                    clearable=False,
                    style={'width': '120px'}
                )
            ], style={'display': 'inline-block', 'marginRight': '30px'}),
            
            # Disease selector
            html.Div([
                html.Label("Select Disease:", style={'font-weight': 'bold', 'marginRight': '10px'}),
                dcc.Dropdown(
                    id="disease-dropdown",
                    options=[{"label": d, "value": d} for d in unique_diseases],
                    value=unique_diseases[0],
                    clearable=False,
                    style={'width': '200px'}
                )
            ], style={'display': 'inline-block', 'marginRight': '30px'}),
            
            # Week interval selector
            html.Div([
                html.Label("Week Interval:", style={'font-weight': 'bold', 'marginRight': '10px'}),
                dcc.Dropdown(
                    id='week-interval',
                    options=[
                        {'label': '4 weeks', 'value': 4},
                        {'label': '12 weeks', 'value': 12},
                        {'label': '24 weeks', 'value': 24}
                    ],
                    value=4,
                    style={'width': '150px'}
                )
            ], style={'display': 'inline-block'})
        ], style={'textAlign': 'center', 'margin': '20px'}),
        
        # Main graph
        dcc.Graph(
            id='main-graph',
            style={'height': '500px', 'width': '1500px'}
            ),
        
        # Modal/Popup for segment details
        html.Div([
            html.Div([
                html.Div([
                    html.H3("Segment Details", style={'textAlign': 'center'}),
                    html.Button("X", id="close-popup", style={
                        'position': 'absolute',
                        'top': '10px',
                        'right': '10px',
                        'border': 'none',
                        'background': 'none',
                        'fontSize': '20px',
                        'cursor': 'pointer'
                    })
                ], style={'borderBottom': '1px solid #ccc', 'padding': '10px', 'position': 'relative'}),
                
                html.Div(id='segment-details', style={'padding': '20px'}),
                
            ], style={
                'backgroundColor': 'white',
                'border': '1px solid #ddd',
                'borderRadius': '5px',
                'width': '400px',
                'maxWidth': '80%',
                'margin': '0 auto',
                'boxShadow': '0px 0px 10px rgba(0,0,0,0.1)'
            })
        ], id='popup-container', style={'display': 'none', 'position': 'fixed', 'top': '0', 'left': '0', 'width': '100%', 'height': '100%', 'backgroundColor': 'rgba(0,0,0,0.5)', 'zIndex': '1000', 'justifyContent': 'center', 'alignItems': 'center'}),
        
        # Store selected segment data
        dcc.Store(id='segment-data')
    ])

    @callback(
        Output('main-graph', 'figure'),
        [Input('year-dropdown', 'value'),
         Input('week-interval', 'value'),
         Input('disease-dropdown', 'value')])
    def update_figure(selected_year, week_interval, selected_disease):
        # Filter by disease and year
        filtered_df = df[(df['Year'] == selected_year) & (df['Disease'] == selected_disease)]
        
        # If no data for selected year/disease
        if filtered_df.empty:
            return px.line(title="No data available for selected parameters")
            
        # Sort by week to ensure correct sequence
        filtered_df = filtered_df.sort_values('Week')
        
        # Create segments based on selected interval
        segments = create_segments(filtered_df, week_interval)
        
        # Calculate APC for each segment
        apc_results = calculate_apc_segments(segments)
        
        if apc_results is None or apc_results.empty:
            return px.line(title="Insufficient data for analysis")
        
        # Create main figure with weekly cases
        fig = px.line(filtered_df, 
                      x="Week", 
                      y="Cases",
                      title=f"{selected_disease} - Weekly Cases ({selected_year})",
                      labels={"Week": "Epidemiological Week", 
                              "Cases": "Confirmed Cases"},
                      markers=True)
        
        # Add annotations for each segment
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown', 'pink', 'gray', 'olive', 'cyan', 'magenta']
        
        for i, segment in enumerate(segments):
            if len(segment) <= 1:
                continue
                
            # Get segment data
            segment_info = apc_results[apc_results['Segment'] == i+1].iloc[0]
            apc = segment_info['APC']
            start_week = segment_info['Start_Week']
            end_week = segment_info['End_Week']
            
            # Color for this segment (color cycle)
            color = colors[i % len(colors)]
            
            # Add trend line
            x_trend = np.arange(start_week, end_week + 1)
            slope = segment_info['Slope']
            intercept = np.log(max(0.01, segment['Cases'].iloc[0])) - slope * 0
            y_trend = np.exp(intercept + slope * np.arange(len(x_trend)))
            
            # Add trend line to graph
            fig.add_trace(
                go.Scatter(
                    x=x_trend,
                    y=y_trend,
                    mode='lines',
                    line=dict(color=color, width=2, dash='dot'),
                    name=f'Trend {i+1}',
                    customdata=[i+1]*len(x_trend)  # Store segment ID
                )
            )
            
            # Highlight segments with different colors
            fig.add_trace(
                go.Scatter(
                    x=segment['Week'],
                    y=segment['Cases'],
                    mode='markers',
                    marker=dict(color=color, size=10),
                    name=f'Segment {i+1}',
                    customdata=[i+1]*len(segment),  # Store segment ID
                    hovertemplate='Week: %{x}<br>Cases: %{y}<br>Click for details<extra></extra>'
                )
            )
            
            # Add vertical line to mark segment start
            fig.add_vline(x=start_week, line_dash="dash", line_color=color, opacity=0.5)
        
        # Customize layout
        fig.update_layout(
            clickmode='event+select',  # Enable clicks to show popup
            hovermode='closest',
            legend_title_text='Segments',
            plot_bgcolor='rgba(240,240,240,0.5)',
            xaxis=dict(
                title='Epidemiological Week',
                gridcolor='white',
                gridwidth=2,
            ),
            yaxis=dict(
                title='Confirmed Cases',
                gridcolor='white',
                gridwidth=2,
                zeroline=True,
                zerolinecolor='black'
            ),
            height=600,
            showlegend=True
        )
        
        return fig

    @callback(
        Output('segment-data', 'data'),
        [Input('main-graph', 'clickData'),
         Input('year-dropdown', 'value'),
         Input('week-interval', 'value'),
         Input('disease-dropdown', 'value')])
    def store_segment_data(click_data, selected_year, week_interval, selected_disease):
        if click_data is None:
            return None
            
        # Get clicked point
        point = click_data['points'][0]
        
        # Check if we have customdata (segment ID)
        if 'customdata' not in point:
            return None
            
        segment_id = point['customdata']
        
        # Fetch complete segment data
        filtered_df = df[(df['Year'] == selected_year) & (df['Disease'] == selected_disease)]
        segments = create_segments(filtered_df.sort_values('Week'), week_interval)
        apc_results = calculate_apc_segments(segments)
        
        if apc_results is None or apc_results.empty:
            return None
            
        # Find specific segment information
        segment_info = apc_results[apc_results['Segment'] == segment_id]
        
        if segment_info.empty:
            return None
            
        # Convert to dictionary and return
        return segment_info.iloc[0].to_dict()

    @callback(
        [Output('popup-container', 'style'),
         Output('segment-details', 'children')],
        [Input('segment-data', 'data'),
         Input('close-popup', 'n_clicks')])
    def show_segment_details(segment_data, close_clicks):
        # Check which input was triggered
        triggered_id = ctx.triggered_id
        
        # If close button was clicked, hide popup
        if triggered_id == 'close-popup':
            return {'display': 'none'}, []
            
        # If we don't have segment data, hide popup
        if segment_data is None:
            return {'display': 'none'}, []
            
        # Style to show popup
        popup_style = {
            'display': 'flex', 
            'position': 'fixed', 
            'top': '0', 
            'left': '0', 
            'width': '100%', 
            'height': '100%', 
            'backgroundColor': 'rgba(0,0,0,0.5)', 
            'zIndex': '1000', 
            'justifyContent': 'center', 
            'alignItems': 'center'
        }
        
        # Format segment details for popup display
        segment_details = [
            html.Div([
                html.H4(f"Segment {int(segment_data['Segment'])}"),
                html.Hr(),
                
                html.Div([
                    html.Div("Period:", style={'fontWeight': 'bold'}),
                    html.Div(f"Weeks {int(segment_data['Start_Week'])} to {int(segment_data['End_Week'])}")
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("Annual Percent Change (APC):", style={'fontWeight': 'bold'}),
                    html.Div(f"{segment_data['APC']:.2f}%", style={
                        'color': 'red' if segment_data['APC'] > 0 else 'green',
                        'fontWeight': 'bold' if abs(segment_data['APC']) > 20 else 'normal'
                    })
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("Coefficient of Determination (R²):", style={'fontWeight': 'bold'}),
                    html.Div(f"{segment_data['R_squared']:.3f}")
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("P-value:", style={'fontWeight': 'bold'}),
                    html.Div(f"{segment_data['P_value']:.4f}")
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("Cases:", style={'fontWeight': 'bold'}),
                    html.Div(f"Start: {int(segment_data['Cases_Start'])} | End: {int(segment_data['Cases_End'])} | Avg: {segment_data['Cases_Avg']:.1f}")
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("Interpretation:", style={'fontWeight': 'bold'}),
                    html.Div(
                        "Significant increase" if segment_data['APC'] > 0 and segment_data['P_value'] < 0.05 else
                        "Significant decrease" if segment_data['APC'] < 0 and segment_data['P_value'] < 0.05 else
                        "No statistically significant change",
                        style={'fontStyle': 'italic'}
                    )
                ])
            ])
        ]
        
        return popup_style, segment_details

    return app

def main():
    df_data = get_notification_data()
    if df_data is None:
        print("Failed to fetch data from database")
        return

    df = process_data(df_data)
    if df is None:
        print("Failed to process data")
        return

    app = create_dash_app(df)
    app.run(debug=True, port=8050)

if __name__ == "__main__":
    main()