from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from itertools import combinations
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load data
logger.info("Loading attribution data...")
try:
    data = pd.read_csv("Input/Dataset/attribution_data.csv")
    logger.info(f"Data loaded successfully: {len(data)} rows, {len(data.columns)} columns")
    logger.info(f"Columns: {list(data.columns)}")
    logger.info(f"Unique channels: {data['channel'].unique().tolist()}")
except Exception as e:
    logger.error(f"Failed to load data: {e}")
    raise

# Attribution Model Functions
def last_touch_model(dt, conv_col, channel_col):
    logger.info("Running Last Touch model...")
    last_touch = dt.loc[dt[conv_col] == 1]
    last_touch_counts = last_touch[channel_col].value_counts()
    last_touch_pct = (last_touch_counts / last_touch_counts.sum() * 100).round(2)
    result = pd.DataFrame({'Conversions': last_touch_counts, 'Weightage': last_touch_pct})
    logger.info(f"Last Touch completed: {len(result)} channels")
    return result

def first_touch_model(dt, conv_col, channel_col, user_id):
    logger.info("Running First Touch model...")
    temp = dt.loc[dt[conv_col] == 1]
    first_touch = temp.groupby(user_id).first().reset_index()
    first_touch_counts = first_touch[channel_col].value_counts()
    first_touch_pct = (first_touch_counts / first_touch_counts.sum() * 100).round(2)
    result = pd.DataFrame({'Conversions': first_touch_counts, 'Weightage': first_touch_pct})
    logger.info(f"First Touch completed: {len(result)} channels")
    return result

def last_non_direct_model(dt, conv_col, channel_col, user_id):
    logger.info("Running Last Non-Direct model...")
    slp = pd.DataFrame(dt.groupby(user_id).tail(2))
    slp = slp[slp[conv_col] == 1]
    slp_grouped = slp.groupby(user_id).first().reset_index()
    last_non_direct_counts = slp_grouped[channel_col].value_counts()
    last_non_direct_pct = (last_non_direct_counts / last_non_direct_counts.sum() * 100).round(2)
    result = pd.DataFrame({'Conversions': last_non_direct_counts, 'Weightage': last_non_direct_pct})
    logger.info(f"Last Non-Direct completed: {len(result)} channels")
    return result

def linear_model(dt, conv_col, channel_col, user_id):
    logger.info("Running Linear model...")
    pd.options.mode.chained_assignment = None
    temp = dt.loc[dt[conv_col] == 1].copy()
    temp['count'] = temp.groupby(user_id)[user_id].transform('count')
    temp['linear_attribution'] = 1 / temp['count']
    linear_attribution = temp.groupby(channel_col)['linear_attribution'].sum()
    linear_pct = (linear_attribution / linear_attribution.sum() * 100).round(2)
    result = pd.DataFrame({'Conversions': linear_attribution, 'Weightage': linear_pct})
    logger.info(f"Linear completed: {len(result)} channels")
    return result

def u_shaped_model(dt, conv_col, channel_col, user_id):
    logger.info("Running U-Shaped model...")
    pd.options.mode.chained_assignment = None
    temp = dt.loc[dt[conv_col] == 1].copy()
    temp['count'] = temp.groupby(user_id)[user_id].transform('count')
    temp['rank'] = temp.groupby(user_id).cumcount() + 1
    
    def calc_attribution(row):
        if row['count'] == 1:
            return 1.0
        elif row['rank'] == 1 or row['rank'] == row['count']:
            return 0.4
        else:
            return 0.2 / (row['count'] - 2) if row['count'] > 2 else 0.2
    
    temp['u_shaped_attribution'] = temp.apply(calc_attribution, axis=1)
    u_shaped_attribution = temp.groupby(channel_col)['u_shaped_attribution'].sum()
    u_shaped_pct = (u_shaped_attribution / u_shaped_attribution.sum() * 100).round(2)
    result = pd.DataFrame({'Conversions': u_shaped_attribution, 'Weightage': u_shaped_pct})
    logger.info(f"U-Shaped completed: {len(result)} channels")
    return result

def pos_decay_model(dt, conv_col, channel_col, user_id):
    logger.info("Running Position Decay model...")
    pd.options.mode.chained_assignment = None
    temp = dt.loc[dt[conv_col] == 1].copy()
    temp['count'] = temp.groupby(user_id)[user_id].transform('count')
    temp['rank'] = temp.groupby(user_id).cumcount() + 1
    
    def calc_attribution(row):
        rel_pos = row['count'] - row['rank']
        return 2 ** rel_pos
    
    temp['pos_decay_attribution'] = temp.apply(calc_attribution, axis=1)
    temp['total_weight'] = temp.groupby(user_id)['pos_decay_attribution'].transform('sum')
    temp['normalized_attribution'] = temp['pos_decay_attribution'] / temp['total_weight']
    pos_decay_attribution = temp.groupby(channel_col)['normalized_attribution'].sum()
    pos_decay_pct = (pos_decay_attribution / pos_decay_attribution.sum() * 100).round(2)
    result = pd.DataFrame({'Conversions': pos_decay_attribution, 'Weightage': pos_decay_pct})
    logger.info(f"Position Decay completed: {len(result)} channels")
    return result

def markov_model(df, conv_col, channel_col, user_id):
    logger.info("Running Markov Chain model...")
    pd.options.mode.chained_assignment = None
    df_paths = df.sort_values(channel_col).groupby(user_id)[channel_col].aggregate(
        lambda x: x.unique().tolist()).reset_index()
    df_conv = df[df[conv_col] == 1].groupby(user_id)[conv_col].sum().reset_index()
    df_paths = df_paths.merge(df_conv, on=user_id, how='left').fillna(0)
    
    list_of_paths = df_paths[channel_col].tolist()
    list_of_unique_channels = set(x for element in list_of_paths for x in element)
    
    total_conversions = df_paths[conv_col].sum()
    base_conversion_rate = total_conversions / len(df_paths) if len(df_paths) > 0 else 0
    
    removal_effects = {}
    for channel in list_of_unique_channels:
        filtered_paths = [path for path in list_of_paths if channel not in path]
        if len(filtered_paths) > 0:
            removal_conversion_rate = len([p for p in filtered_paths]) / len(df_paths)
            removal_effects[channel] = base_conversion_rate - removal_conversion_rate
        else:
            removal_effects[channel] = base_conversion_rate
    
    re_sum = sum(removal_effects.values())
    markov_attribution = {k: (v / re_sum * total_conversions) if re_sum > 0 else 0 
                         for k, v in removal_effects.items()}
    
    markov_df = pd.DataFrame(list(markov_attribution.items()), columns=[channel_col, 'Conversions'])
    markov_df = markov_df.set_index(channel_col)
    total = markov_df['Conversions'].sum()
    markov_df['Weightage'] = (markov_df['Conversions'] / total * 100).round(2) if total > 0 else 0
    logger.info(f"Markov Chain completed: {len(markov_df)} channels")
    return markov_df

def shapley_model(df, conv_col, channel_col, user_id):
    logger.info("Running Shapley Value model...")
    dt_paths = df.sort_values(channel_col).groupby(user_id)[channel_col].aggregate(
        lambda x: x.unique().tolist()).reset_index()
    dt_conv = df[df[conv_col] == 1].groupby(user_id)[conv_col].sum().reset_index()
    dt_paths = dt_paths.merge(dt_conv, on=user_id, how='left').fillna(0)
    
    all_channels = set()
    for path in dt_paths[channel_col]:
        all_channels.update(path)
    all_channels = list(all_channels)
    
    def get_conversion_value(channels, paths_df):
        if len(channels) == 0:
            return 0
        matching_paths = paths_df[paths_df[channel_col].apply(
            lambda x: all(c in x for c in channels))]
        return matching_paths[conv_col].sum()
    
    shapley_values = {}
    n = len(all_channels)
    
    for channel in all_channels:
        shapley_value = 0
        other_channels = [c for c in all_channels if c != channel]
        
        for r in range(len(other_channels) + 1):
            for subset in combinations(other_channels, r):
                subset_list = list(subset)
                with_channel = get_conversion_value(subset_list + [channel], dt_paths)
                without_channel = get_conversion_value(subset_list, dt_paths)
                weight = 1 / (n * len(list(combinations(other_channels, r)))) if len(list(combinations(other_channels, r))) > 0 else 0
                shapley_value += weight * (with_channel - without_channel)
        
        shapley_values[channel] = max(0, shapley_value)
    
    shapley_df = pd.DataFrame(list(shapley_values.items()), columns=[channel_col, 'Conversions'])
    shapley_df = shapley_df.set_index(channel_col)
    total = shapley_df['Conversions'].sum()
    shapley_df['Weightage'] = (shapley_df['Conversions'] / total * 100).round(2) if total > 0 else 0
    logger.info(f"Shapley Value completed: {len(shapley_df)} channels")
    return shapley_df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_attribution', methods=['POST'])
def run_attribution():
    logger.info("=" * 60)
    logger.info("Starting attribution analysis...")
    try:
        # Run all attribution models (excluding Shapley for performance)
        last_touch = last_touch_model(data, 'conversion', 'channel')
        first_touch = first_touch_model(data, 'conversion', 'channel', 'cookie')
        last_non_direct = last_non_direct_model(data, 'conversion', 'channel', 'cookie')
        linear = linear_model(data, 'conversion', 'channel', 'cookie')
        u_shaped = u_shaped_model(data, 'conversion', 'channel', 'cookie')
        pos_decay = pos_decay_model(data, 'conversion', 'channel', 'cookie')
        markov = markov_model(data, 'conversion', 'channel', 'cookie')
        
        logger.info("All models completed successfully")
        
        # Get all unique channels
        all_channels = set()
        for df in [last_touch, first_touch, last_non_direct, linear, u_shaped, pos_decay, markov]:
            all_channels.update(df.index.tolist())
        
        logger.info(f"Processing {len(all_channels)} channels: {sorted(all_channels)}")
        
        # Create combined results
        combined = {}
        for channel in all_channels:
            combined[channel] = {
                'LastTouch': float(last_touch.loc[channel, 'Weightage']) if channel in last_touch.index else 0.0,
                'FirstTouch': float(first_touch.loc[channel, 'Weightage']) if channel in first_touch.index else 0.0,
                'LastNonDirect': float(last_non_direct.loc[channel, 'Weightage']) if channel in last_non_direct.index else 0.0,
                'Linear': float(linear.loc[channel, 'Weightage']) if channel in linear.index else 0.0,
                'UShaped': float(u_shaped.loc[channel, 'Weightage']) if channel in u_shaped.index else 0.0,
                'PositionDecay': float(pos_decay.loc[channel, 'Weightage']) if channel in pos_decay.index else 0.0,
                'Markov': float(markov.loc[channel, 'Weightage']) if channel in markov.index else 0.0
            }
            values = list(combined[channel].values())
            combined[channel]['Mean'] = round(float(np.mean(values)), 2)
        
        logger.info("Combined results created")
        
        # Calculate analytics
        total_conversions = int(data[data['conversion'] == 1].shape[0])
        total_interactions = int(data.shape[0])
        conversion_rate = round(float(total_conversions / total_interactions * 100), 2)
        unique_users = int(data['cookie'].nunique())
        
        logger.info(f"Analytics: {total_conversions} conversions, {total_interactions} interactions, {conversion_rate}% rate")
        
        # Channel statistics
        channel_stats = {}
        for channel in all_channels:
            channel_data = data[data['channel'] == channel]
            channel_conversions = int(channel_data[channel_data['conversion'] == 1].shape[0])
            channel_interactions = int(channel_data.shape[0])
            conv_data = channel_data[channel_data['conversion'] == 1]
            avg_value = float(conv_data['conversion_value'].mean()) if len(conv_data) > 0 else 0.0
            
            channel_stats[channel] = {
                'interactions': channel_interactions,
                'conversions': channel_conversions,
                'conversion_rate': round(float(channel_conversions / channel_interactions * 100), 2) if channel_interactions > 0 else 0.0,
                'avg_conversion_value': round(avg_value, 2)
            }
        
        analytics = {
            'total_conversions': total_conversions,
            'total_interactions': total_interactions,
            'conversion_rate': conversion_rate,
            'unique_users': unique_users,
            'channel_stats': channel_stats
        }
        
        logger.info("Attribution analysis completed successfully")
        logger.info("=" * 60)
        
        return jsonify({
            'success': True, 
            'results': combined, 
            'analytics': analytics
        })
    
    except Exception as e:
        logger.error(f"Error in attribution analysis: {str(e)}", exc_info=True)
        import traceback
        return jsonify({
            'success': False, 
            'error': str(e), 
            'traceback': traceback.format_exc()
        })

@app.route('/optimize_budget', methods=['POST'])
def optimize_budget():
    logger.info("Starting budget optimization...")
    try:
        budget = float(request.json.get('budget', 1000))
        channel_limits = request.json.get('channel_limits', {})
        mean_attributions = request.json.get('mean_attributions', {})
        
        logger.info(f"Budget: ${budget}, Channels: {len(mean_attributions)}")
        
        channels = list(mean_attributions.keys())
        weights = np.array([mean_attributions[ch] for ch in channels])
        weights = weights / weights.sum()
        
        allocations = weights * budget
        
        for i, channel in enumerate(channels):
            if channel in channel_limits:
                limit = float(channel_limits[channel])
                if allocations[i] > limit:
                    allocations[i] = limit
        
        total_allocated = allocations.sum()
        if total_allocated < budget:
            remaining = budget - total_allocated
            for i in range(len(channels)):
                if channels[i] not in channel_limits or allocations[i] < float(channel_limits[channels[i]]):
                    allocations[i] += remaining * weights[i]
        
        result = {channel: round(float(alloc), 2) for channel, alloc in zip(channels, allocations)}
        
        logger.info(f"Budget optimization completed: {result}")
        return jsonify({'success': True, 'allocations': result})
    
    except Exception as e:
        logger.error(f"Error in budget optimization: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    logger.info("Starting Flask application on port 5000...")
    app.run(debug=True, port=5000, use_reloader=False)
