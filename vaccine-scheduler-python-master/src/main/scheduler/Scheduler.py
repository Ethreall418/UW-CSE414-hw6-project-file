from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime


'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None


def create_patient(tokens):
    if len(tokens) != 3:
        print("Create patient failed.")
        return
    username = tokens[1]
    password = tokens[2]

    if username_exists_patient(username):
        print("Username taken, try again!")
        return
    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    patient = Patient(username, salt=salt, hash=hash)

    try:
        patient.save_to_db()
        print(f'Created user {username}')
    except pymssql.Error as e:
        print("Create patient failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Create patient failed.")
        print(e)
        return

#took from the username_exists_caregiver example below
def username_exists_patient(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Patients WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False

def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        return

    username = tokens[1]
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists_caregiver(username):
        print("Username taken, try again!")
        return

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    caregiver = Caregiver(username, salt=salt, hash=hash)

    # save to caregiver information to our database
    try:
        caregiver.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def login_patient(tokens):
    global current_patient
    if current_patient is not None or current_patient is not None:
        print('User already logged in, try again')
        return

    if len(tokens) != 3:
        print('Login patient failed')
        return

    username = tokens[1]
    password = tokens[2]

    patient = None
    try:
        patient = Patient(username, password=password).get()
    except pymssql.Error as e:
        print("Login patient failed.")
        quit()
    except Exception as e:
        print("Login patient failed.")
        return
    print(f'Logged in as {username}')
    current_patient = patient

def login_caregiver(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_caregiver
    if current_caregiver is not None or current_patient is not None:
        print("User already logged in.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        return

    username = tokens[1]
    password = tokens[2]

    caregiver = None
    try:
        caregiver = Caregiver(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if caregiver is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_caregiver = caregiver


def search_caregiver_schedule(tokens):
    if len(tokens) != 2:
        print('Please try again.')
        return

    date_str = tokens[1]
    try:
        date = datetime.datetime.strptime(date_str, '%m-%d-%Y')
    except ValueError:
        print('Invalid date. Please try again')
        return

    if current_patient is None and current_caregiver is None:
        print('Please login first.')
        return

    search_all_caregiver_by_date(date)
    show_available_vaccines()

#to search available caregivers by date
def search_all_caregiver_by_date(date):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cusor(as_dict=True)

    query = 'SELECT Username FROM Availabilities WHERE Time = %s ORDER BY Username ASC'
    result_str = ''
    try:
        cursor.execute(query,(date,))
        result = cursor.fetchall()
        if result:
            for row in result:
                result_str += row['Username']+''
            print(result_str)
        else:
            print('No available caregiver. Please try again.')
    except pymssql.Error:
        print('Database failed, please try again.')
    finally:
        cm.close_connection()

#to search available vaccines
def show_available_vaccines():
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    query = 'SELECT * FROM Vaccines'
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        if result:
            for row in result:
                print(row['Name'], row['Doses'])
        else:
            print('No available vaccines, please try again.')
    except pymssql.Error:
        print('Database failed, please try again.')
    finally:
        cm.close_connection()

def reserve(tokens):
    global current_caregiver
    global current_patient

    if current_caregiver is not None:
        print('Please login as a patient.')
        return

    if current_patient is None:
        print('Please login first.')
        return

    if len(tokens) != 3:
        print('Please try again.')
        return

    date_str, vaccine = tokens[1], tokens[2]
    try:
        date = datetime.datetime.strptime(date_str, '%m-%d-%Y')
    except ValueError:
        print('Invalid date. Please try again')
        return

    caregiver = choose_available_caregiver(date)
    if caregiver is None:
        return
    if not check_vaccine(vaccine):
        return
    update_available_caregivers(caregiver, date)
    create_appointment(date, current_patient, caregiver, vaccine)


def choose_available_caregiver(date):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    query = 'SELECT Username FROM Availabilities WHERE Time = %s ORDER BY Username ASC'
    try:
        cursor.execute(query, (date,))
        result = cursor.fetchall()
        if result:
            caregivers_all = [row['Username'] for row in result]
            reserve_caregiver = caregivers_all[0]
            cm.close_connection()
            return reserve_caregiver
        else:
            print('No care giver is available.')
            cm.close_connection()
            return
    except pymssql.Error:
        print('Database failed, please try again.')
        cm.close_connection()
        return

def check_vaccine(vaccine_name):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    query = 'SELECT Name, Doses FROM Vaccines WHERE Name = %s'

    try:
        cursor.execute(query, vaccine_name)
        vaccine_list = cursor.fetchall()
        if len(vaccine_list) == 0:
            print('Not enough available doses')
            cm.close_connection()
            return False
        for row in vaccine_list:
            doses = row[1]
            if doses > 0:
                doses -= 1
                cursor.execute('UPDATE Vaccines SET Doses = %s WHERE Name = %s', (doses, vaccine_name))
                conn.commit()
            else:
                print('Not enough available doses.')
    except pymssql.Error:
        print('Database failed. Please try again.')
        cm.close_connection()
        return

def update_available_caregivers(caregiver_name, date):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    query = 'DELETE FROM Availabilities WHERE Time = %s AND Username = %s'
    try:
        cursor.execute(query, (date,))
        conn.commit()
    except pymssql.Error:
        print('Database failed. Please try again.')
        cm.close_connection()
        return
    cm.close_connection()

def create_appointment(date, patient_name, caregiver_name, vaccine_name):
    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    query = 'INSERT INTO Appointments (Time, Patient_name, Caregiver_name, Vaccine_name) VALUES (%s, %s, %s, %s)'
    try:
        cursor.execute(query,(date, patient_name, caregiver_name, vaccine_name))
        conn.commit()
        cursor.execute('SELECT SCOPE_IDENTITY()') # This is a way to obtain the ID which I found from online resources.
        appointment_id = cursor.fetchone()[0]
        print('Appointment ID ' + str(appointment_id) + ', Caregiver username ' + caregiver_name)
    except pymssql.Error:
        print('Database failed. Please try again.')
        cm.close_connection()
        return
    cm.close_connection()

def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        return

    date = tokens[1]
    # assume input is hyphenated in the format mm-dd-yyyy
    date_tokens = date.split("-")
    month = int(date_tokens[0])
    day = int(date_tokens[1])
    year = int(date_tokens[2])
    try:
        d = datetime.datetime(year, month, day)
        current_caregiver.upload_availability(d)
    except pymssql.Error as e:
        print("Upload Availability Failed")
        print("Db-Error:", e)
        quit()
    except ValueError:
        print("Please enter a valid date!")
        return
    except Exception as e:
        print("Error occurred when uploading availability")
        print("Error:", e)
        return
    print("Availability uploaded!")


def cancel(tokens):
    """
    TODO: Extra Credit
    """
    pass


def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        return

    vaccine_name = tokens[1]
    doses = int(tokens[2])
    vaccine = None
    try:
        vaccine = Vaccine(vaccine_name, doses).get()
    except pymssql.Error as e:
        print("Error occurred when adding doses")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when adding doses")
        print("Error:", e)
        return

    # if the vaccine is not found in the database, add a new (vaccine, doses) entry.
    # else, update the existing entry by adding the new doses
    if vaccine is None:
        vaccine = Vaccine(vaccine_name, doses)
        try:
            vaccine.save_to_db()
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            vaccine.increase_available_doses(doses)
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    print("Doses updated!")


def show_appointments():
    global current_caregiver
    global current_patient

    if current_caregiver is None and current_patient is None:
        print('Please log in first.')
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor(as_dict=True)

    try:
        if current_patient:
            user_type = 'Patient'
            query = 'SELECT * FROM Appointments WHERE Patient_name=%s ORDER BY ID ASC'
            user_name = current_patient.username
        elif current_caregiver:
            user_type = 'Caregiver'
            query = 'SELECT * FROM Appointments WHERE Caregiver_name=%s ORDER BY ID ASC'
            user_name = current_caregiver.username

        cursor.execute(query, (user_name,))
        results = cursor.fetchall()

        if not results:
            print('No appointments found.')
            return

        for row in results:
            print(row['ID'], row['Vaccine_name'], row['Time'], row[row['Patient_name'] if user_type == 'Caregiver' else 'Caregiver_name'])

    except pymssql.Error:
        print('Database failed, please try again')
    finally:
        cm.close_connection()

def logout(tokens):
    global current_caregiver
    global current_patient

    try:
        if current_patient is None and current_caregiver is None:
            print("Please login first.")
            return
        else:
            current_caregiver=None
            current_patient=None
            print("Successfully logged out.")
            return
    except pymssql.Error:
        print("Datebase failed. Please try again!")
        return


def start():
    stop = False
    print()
    print(" *** Please enter one of the following commands *** ")
    print("> create_patient <username> <password>")  # //TODO: implement create_patient (Part 1)
    print("> create_caregiver <username> <password>")
    print("> login_patient <username> <password>")  # // TODO: implement login_patient (Part 1)
    print("> login_caregiver <username> <password>")
    print("> search_caregiver_schedule <date>")  # // TODO: implement search_caregiver_schedule (Part 2)
    print("> reserve <date> <vaccine>")  # // TODO: implement reserve (Part 2)
    print("> upload_availability <date>")
    print("> cancel <appointment_id>")  # // TODO: implement cancel (extra credit)
    print("> add_doses <vaccine> <number>")
    print("> show_appointments")  # // TODO: implement show_appointments (Part 2)
    print("> logout")  # // TODO: implement logout (Part 2)
    print("> Quit")
    print()
    while not stop:
        response = ""
        print("> ", end='')

        try:
            response = str(input())
        except ValueError:
            print("Please try again!")
            break

        response = response.lower()
        tokens = response.split(" ")
        if len(tokens) == 0:
            ValueError("Please try again!")
            continue
        operation = tokens[0]
        if operation == "create_patient":
            create_patient(tokens)
        elif operation == "create_caregiver":
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == cancel:
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "quit":
            print("Bye!")
            stop = True
        else:
            print("Invalid operation name!")


if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
