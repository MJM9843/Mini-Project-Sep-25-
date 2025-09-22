import boto3
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import os
from functools import wraps
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# AWS DynamoDB configuration
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# DynamoDB tables
gyms_table = dynamodb.Table('Gyms')
bookings_table = dynamodb.Table('Bookings')
time_slots_table = dynamodb.Table('TimeSlots')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'gym_owner_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_gyms', methods=['POST'])
def search_gyms():
    location = request.form.get('location', '').lower()
    date = request.form.get('date')
    
    try:
        # Scan gyms table for matching location
        response = gyms_table.scan()
        gyms = []
        
        for item in response['Items']:
            if location in item.get('location', '').lower():
                gym_data = {
                    'gym_id': item['gym_id'],
                    'gym_name': item['gym_name'],
                    'location': item['location'],
                    'description': item['description'],
                    'owner_name': item['owner_name']
                }
                
                # Get available slots for the selected date
                slots_response = time_slots_table.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('gym_id').eq(item['gym_id']),
                    FilterExpression=boto3.dynamodb.conditions.Attr('date').eq(date) & 
                                   boto3.dynamodb.conditions.Attr('is_available').eq(True)
                )
                gym_data['available_slots'] = slots_response.get('Items', [])
                gyms.append(gym_data)
        
        return render_template('search_results.html', gyms=gyms, selected_date=date)
    
    except Exception as e:
        flash(f'Error searching gyms: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/book_session', methods=['POST'])
def book_session():
    gym_id = request.form.get('gym_id')
    slot_id = request.form.get('slot_id')
    user_name = request.form.get('user_name')
    user_phone = request.form.get('user_phone')
    date = request.form.get('date')
    time_slot = request.form.get('time_slot')
    
    try:
        # Create booking
        booking_id = str(uuid.uuid4())
        booking_data = {
            'booking_id': booking_id,
            'gym_id': gym_id,
            'slot_id': slot_id,
            'user_name': user_name,
            'user_phone': user_phone,
            'date': date,
            'time_slot': time_slot,
            'booking_timestamp': datetime.now().isoformat(),
            'status': 'confirmed'
        }
        
        bookings_table.put_item(Item=booking_data)
        
        # Update slot availability
        time_slots_table.update_item(
            Key={'gym_id': gym_id, 'slot_id': slot_id},
            UpdateExpression='SET is_available = :val',
            ExpressionAttributeValues={':val': False}
        )
        
        # Get gym details for confirmation
        gym_response = gyms_table.get_item(Key={'gym_id': gym_id})
        gym_data = gym_response.get('Item', {})
        
        booking_info = {
            'booking_id': booking_id,
            'gym_name': gym_data.get('gym_name'),
            'location': gym_data.get('location'),
            'date': date,
            'time_slot': time_slot,
            'user_name': user_name
        }
        
        return render_template('booking_confirmation.html', booking=booking_info)
    
    except Exception as e:
        flash(f'Error booking session: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/register', methods=['POST'])
def register():
    owner_name = request.form.get('owner_name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    password = request.form.get('password')
    gym_name = request.form.get('gym_name')
    location = request.form.get('location')
    description = request.form.get('description')
    
    try:
        gym_id = str(uuid.uuid4())
        hashed_password = generate_password_hash(password)
        
        gym_data = {
            'gym_id': gym_id,
            'owner_name': owner_name,
            'phone': phone,
            'email': email,
            'password': hashed_password,
            'gym_name': gym_name,
            'location': location,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        gyms_table.put_item(Item=gym_data)
        
        flash('Gym registered successfully! You can now login.', 'success')
        return redirect(url_for('login'))
    
    except Exception as e:
        flash(f'Error registering gym: {str(e)}', 'error')
        return redirect(url_for('signup'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    email = request.form.get('email')
    password = request.form.get('password')
    
    try:
        # Scan for gym owner by email
        response = gyms_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('email').eq(email)
        )
        
        if response['Items']:
            gym_owner = response['Items'][0]
            if check_password_hash(gym_owner['password'], password):
                session['gym_owner_id'] = gym_owner['gym_id']
                session['gym_name'] = gym_owner['gym_name']
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials', 'error')
        else:
            flash('Gym owner not found', 'error')
    
    except Exception as e:
        flash(f'Login error: {str(e)}', 'error')
    
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    gym_id = session['gym_owner_id']
    
    try:
        # Get gym bookings
        response = bookings_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('gym_id').eq(gym_id)
        )
        bookings = response.get('Items', [])
        
        # Get available time slots
        slots_response = time_slots_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('gym_id').eq(gym_id)
        )
        time_slots = slots_response.get('Items', [])
        
        return render_template('dashboard.html', bookings=bookings, time_slots=time_slots)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/add_time_slot', methods=['POST'])
@login_required
def add_time_slot():
    gym_id = session['gym_owner_id']
    date = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    capacity = int(request.form.get('capacity', 1))
    
    try:
        slot_id = str(uuid.uuid4())
        time_slot_data = {
            'gym_id': gym_id,
            'slot_id': slot_id,
            'date': date,
            'start_time': start_time,
            'end_time': end_time,
            'time_slot': f"{start_time} - {end_time}",
            'capacity': capacity,
            'is_available': True,
            'created_at': datetime.now().isoformat()
        }
        
        time_slots_table.put_item(Item=time_slot_data)
        flash('Time slot added successfully!', 'success')
    
    except Exception as e:
        flash(f'Error adding time slot: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/cancel_booking/<booking_id>')
@login_required
def cancel_booking(booking_id):
    try:
        # Get booking details
        response = bookings_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('booking_id').eq(booking_id)
        )
        
        if response['Items']:
            booking = response['Items'][0]
            
            # Update booking status
            bookings_table.update_item(
                Key={'booking_id': booking_id},
                UpdateExpression='SET #status = :val',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':val': 'cancelled'}
            )
            
            # Make slot available again
            time_slots_table.update_item(
                Key={'gym_id': booking['gym_id'], 'slot_id': booking['slot_id']},
                UpdateExpression='SET is_available = :val',
                ExpressionAttributeValues={':val': True}
            )
            
            flash('Booking cancelled successfully!', 'success')
        else:
            flash('Booking not found', 'error')
    
    except Exception as e:
        flash(f'Error cancelling booking: {str(e)}', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
