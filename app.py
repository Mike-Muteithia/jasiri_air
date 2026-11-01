from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, Flight, Passenger, Booking, Administrator, ContactMessage
from datetime import date, time
import string
import random

app = Flask(__name__)
# Secret key is required for Flask sessions and flash messages
app.config['SECRET_KEY'] = 'jasiri-air-academic-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flight_ticketing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Automatically create tables and seed initial data
with app.app_context():
    db.create_all()
    
    # Seed Administrator Account
    if not Administrator.query.filter_by(username='admin').first():
        admin = Administrator(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        
    # Seed Sample Flights from Rubric
    if not Flight.query.first():
        f1 = Flight(
            flight_number='SL101',
            airline_name='Jasiri Air',
            departure_city='Nairobi',
            destination_city='Mombasa',
            departure_date=date(2026, 12, 10),
            departure_time=time(8, 0),
            arrival_time=time(9, 15),
            travel_class='Economy',
            ticket_price=8500.00,
            total_seats=150,
            available_seats=150
        )
        f2 = Flight(
            flight_number='SL205',
            airline_name='Jasiri Air',
            departure_city='Nairobi',
            destination_city='Kisumu',
            departure_date=date(2026, 12, 11),
            departure_time=time(10, 30),
            arrival_time=time(11, 25),
            travel_class='Economy',
            ticket_price=6500.00,
            total_seats=100,
            available_seats=100
        )
        db.session.add_all([f1, f2])
    
    db.session.commit()

# Replace the temporary index route with this:
@app.route('/')
def index():
    # Pass today's date to Jinja2 to enforce the 'min' attribute on the date picker
    return render_template('index.html', today_date=date.today().strftime('%Y-%m-%d'))

@app.route('/search')
def search_flights():
    departure = request.args.get('departure', '')
    destination = request.args.get('destination', '')
    flight_date_str = request.args.get('date', '')
    passengers = request.args.get('passengers', 1, type=int)
    travel_class = request.args.get('travel_class', '')

    # Base query: Only show flights that have enough seats for the requested passengers
    query = Flight.query.filter(Flight.available_seats >= passengers)
    
    # Apply filters dynamically if the user provided them
    if departure:
        query = query.filter(Flight.departure_city.ilike(f'%{departure}%'))
    if destination:
        query = query.filter(Flight.destination_city.ilike(f'%{destination}%'))
    if flight_date_str:
        query = query.filter(Flight.departure_date == date.fromisoformat(flight_date_str))
    if travel_class:
        query = query.filter(Flight.travel_class == travel_class)
        
    flights = query.all()
    
    return render_template('search_flights.html', flights=flights, passengers=passengers)

def generate_pnr():
    """Generates an 8-character alphanumeric booking reference."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@app.route('/book/<int:flight_id>', methods=['GET', 'POST'])
def book_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    passengers = request.args.get('passengers', 1, type=int)

    if request.method == 'POST':
        # Retrieve form data
        name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        id_num = request.form.get('identification_number')
        passengers_to_book = int(request.form.get('passengers', 1))

        # Validation: Check seat availability before confirming
        if flight.available_seats < passengers_to_book:
            flash('Not enough seats available on this flight!', 'danger')
            return redirect(url_for('search_flights'))

        # Create the passenger record
        new_passenger = Passenger(
            full_name=name, email=email, phone=phone, identification_number=id_num
        )
        db.session.add(new_passenger)
        db.session.commit() # Commit to generate the passenger_id

        # Calculate costs and generate PNR
        total_cost = flight.ticket_price * passengers_to_book
        pnr = generate_pnr()

        # Create the booking record
        new_booking = Booking(
            booking_reference=pnr,
            passenger_id=new_passenger.passenger_id,
            flight_id=flight.flight_id,
            number_of_passengers=passengers_to_book,
            travel_class=flight.travel_class,
            total_cost=total_cost,
            booking_status="Confirmed"
        )
        
        # Decrement available seats consistently
        flight.available_seats -= passengers_to_book

        db.session.add(new_booking)
        db.session.commit()

        flash('Booking successful!', 'success')
        return redirect(url_for('booking_confirmation', pnr=pnr))

    return render_template('booking.html', flight=flight, passengers=passengers)

@app.route('/ticket/<pnr>')
def booking_confirmation(pnr):
    # Retrieve the booking by its PNR. first_or_404 ensures invalid PNRs return a 404 error page.
    booking = Booking.query.filter_by(booking_reference=pnr).first_or_404()
    return render_template('booking_confirmation.html', booking=booking)

@app.route('/my-bookings', methods=['GET', 'POST'])
def my_bookings():
    booking = None
    if request.method == 'POST':
        pnr = request.form.get('pnr', '').strip().upper()
        email = request.form.get('email', '').strip()
        
        # Query combining Booking and Passenger to enforce the email verification requirement
        booking = Booking.query.join(Passenger).filter(
            Booking.booking_reference == pnr,
            Passenger.email == email
        ).first()
        
        if not booking:
            flash('No booking found with the provided details.', 'danger')
            
    return render_template('my_bookings.html', booking=booking)

@app.route('/cancel-booking/<pnr>', methods=['POST'])
def cancel_booking(pnr):
    booking = Booking.query.filter_by(booking_reference=pnr).first_or_404()
    
    # Ensure we only cancel active bookings and release the seats
    if booking.booking_status != 'Cancelled':
        booking.booking_status = 'Cancelled'
        booking.flight.available_seats += booking.number_of_passengers
        db.session.commit()
        flash(f'Booking {pnr} has been successfully cancelled.', 'success')
    else:
        flash('This booking is already cancelled.', 'warning')
        
    return redirect(url_for('my_bookings'))

# --- Admin Authentication Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Unauthorized access. Please log in as an administrator.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Administrator.query.filter_by(username=username).first()
        
        # Verify user exists and password is correct
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_id'] = admin.admin_id
            session['username'] = admin.username
            flash('Welcome to the Admin Dashboard.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Read operation: Fetch all flights for the admin to manage
    flights = Flight.query.all()
    return render_template('admin/dashboard.html', flights=flights)

@app.route('/admin/flight/add', methods=['GET', 'POST'])
@admin_required
def add_flight():
    if request.method == 'POST':
        # Convert HTML date/time strings to Python objects
        dep_date = date.fromisoformat(request.form.get('departure_date'))
        dep_time = time.fromisoformat(request.form.get('departure_time'))
        arr_time = time.fromisoformat(request.form.get('arrival_time'))
        
        total_seats = int(request.form.get('total_seats'))
        
        new_flight = Flight(
            flight_number=request.form.get('flight_number').upper(),
            airline_name=request.form.get('airline_name', 'SkyLink Airlines'),
            departure_city=request.form.get('departure_city'),
            destination_city=request.form.get('destination_city'),
            departure_date=dep_date,
            departure_time=dep_time,
            arrival_time=arr_time,
            travel_class=request.form.get('travel_class'),
            ticket_price=float(request.form.get('ticket_price')),
            total_seats=total_seats,
            available_seats=total_seats # New flights start with all seats available
        )
        
        db.session.add(new_flight)
        db.session.commit()
        flash('New flight added successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin/add_flight.html')

@app.route('/admin/flight/edit/<int:flight_id>', methods=['GET', 'POST'])
@admin_required
def edit_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    
    if request.method == 'POST':
        flight.flight_number = request.form.get('flight_number').upper()
        flight.airline_name = request.form.get('airline_name')
        flight.departure_city = request.form.get('departure_city')
        flight.destination_city = request.form.get('destination_city')
        flight.departure_date = date.fromisoformat(request.form.get('departure_date'))
        flight.departure_time = time.fromisoformat(request.form.get('departure_time'))
        flight.arrival_time = time.fromisoformat(request.form.get('arrival_time'))
        flight.travel_class = request.form.get('travel_class')
        flight.ticket_price = float(request.form.get('ticket_price'))
        
        # Safely adjust available seats if the total capacity is changed
        new_total = int(request.form.get('total_seats'))
        seat_difference = new_total - flight.total_seats
        flight.total_seats = new_total
        flight.available_seats += seat_difference 
        
        db.session.commit()
        flash('Flight updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin/edit_flight.html', flight=flight)

@app.route('/admin/flight/delete/<int:flight_id>', methods=['POST'])
@admin_required
def delete_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    
    # Validation: Prevent deletion if there are active bookings
    active_bookings = Booking.query.filter_by(flight_id=flight.flight_id, booking_status='Confirmed').first()
    if active_bookings:
        flash('Cannot delete this flight because it has active confirmed bookings.', 'danger')
    else:
        db.session.delete(flight)
        db.session.commit()
        flash('Flight deleted successfully.', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/bookings', methods=['GET'])
@admin_required
def manage_bookings():
    search_query = request.args.get('search', '').strip()
    
    # Filter bookings by PNR, Flight Number, or Status if a search term is provided
    if search_query:
        bookings = Booking.query.join(Flight).filter(
            (Booking.booking_reference.ilike(f'%{search_query}%')) |
            (Booking.booking_status.ilike(f'%{search_query}%')) |
            (Flight.flight_number.ilike(f'%{search_query}%'))
        ).all()
    else:
        bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
        
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        new_msg = ContactMessage(
            customer_name=request.form.get('customer_name'),
            email=request.form.get('email'),
            subject=request.form.get('subject'),
            message=request.form.get('message')
        )
        db.session.add(new_msg)
        db.session.commit()
        flash('Thank you for contacting us. Your message has been received.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)