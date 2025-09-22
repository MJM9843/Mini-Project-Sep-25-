import boto3

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Create Gyms table
def create_gyms_table():
    table = dynamodb.create_table(
        TableName='Gyms',
        KeySchema=[
            {
                'AttributeName': 'gym_id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'gym_id',
                'AttributeType': 'S'
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    table.wait_until_exists()
    print("Gyms table created successfully!")

# Create Bookings table
def create_bookings_table():
    table = dynamodb.create_table(
        TableName='Bookings',
        KeySchema=[
            {
                'AttributeName': 'booking_id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'booking_id',
                'AttributeType': 'S'
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    table.wait_until_exists()
    print("Bookings table created successfully!")

# Create TimeSlots table
def create_time_slots_table():
    table = dynamodb.create_table(
        TableName='TimeSlots',
        KeySchema=[
            {
                'AttributeName': 'gym_id',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'slot_id',
                'KeyType': 'RANGE'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'gym_id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'slot_id',
                'AttributeType': 'S'
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    table.wait_until_exists()
    print("TimeSlots table created successfully!")

if __name__ == '__main__':
    try:
        create_gyms_table()
        create_bookings_table()
        create_time_slots_table()
        print("All tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
