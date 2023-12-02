from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3 as sql
import os
import pandas as pd
import random as rnd
from enum import Enum
import prettytable as prettytable

# ... (Your existing code for classes and DBMgr)
POPULATION_SIZE = 10
NUMB_OF_ELITE_SCHEDULES = 1
TOURNAMENT_SELECTION_SIZE = 3
MUTATION_RATE = 0.1

class DBMgr:
    def __init__(self):
        self._conn = sql.connect('class_schedule.db')
        self._c = self._conn.cursor()
        self._rooms = self._select_rooms()
        self._timings = self._select_timings()
        self._faculties = self._select_faculties()
        self._courses = self._select_courses()
        self._depts = self._select_depts()
        self._numberOfClasses = 0
        for i in range(0, len(self._depts)):
            self._numberOfClasses += len(self._depts[i].get_courses())
    def _select_rooms(self):
        self._c.execute("SELECT * FROM room")
        rooms = self._c.fetchall()
        returnRooms = []
        for i in range(0, len(rooms)):
            returnRooms.append(Room(rooms[i][0], rooms[i][1]))
        return returnRooms
    def _select_timings(self):
        self._c.execute("SELECT * FROM timing")
        timings = self._c.fetchall()
        returnTimings = []
        for i in range(0, len(timings)):
            returnTimings.append(Timing(timings[i][0], timings[i][1]))
        return returnTimings
    def _select_faculties(self):
        self._c.execute("SELECT * FROM faculty")
        faculties = self._c.fetchall()
        returnFaculties = []
        for i in range(0, len(faculties)):
            returnFaculties.append(Faculty(faculties[i][0], faculties[i][1], self._select_faculty_availability(faculties[i][0])))
        return returnFaculties
    def _select_faculty_availability(self, faculty):
        self._c.execute("SELECT * from faculty_availability where faculty_id = '" + faculty + "'")
        facultySsRS = self._c.fetchall()
        facultySs = []
        for i in range(0, len(facultySsRS)): facultySs.append(facultySsRS[i][1])
        facultyAvailability = list()
        for i in range(0, len(self._timings)):
            if self._timings[i].get_id() in facultySs:
                facultyAvailability.append(self._timings[i])
        return facultyAvailability
    def _select_courses(self):
        self._c.execute("SELECT * FROM course")
        courses = self._c.fetchall()
        returnCourses = []
        for i in range(0, len(courses)):
            returnCourses.append(Course(courses[i][0], courses[i][1], self._select_course_faculties(courses[i][0]), courses[i][2]))
        return returnCourses
    def _select_depts(self):
        self._c.execute("SELECT * FROM dept")
        depts = self._c.fetchall()
        returnDepts = []
        for i in range(0, len(depts)):
            returnDepts.append(Department(depts[i][0], self._select_dept_courses(depts[i][0])))
        return returnDepts
    def _select_course_faculties(self, courseNumber):
        self._c.execute("SELECT * FROM course_faculty where course_number == '" + courseNumber + "'")
        dbFacultyNumbers = self._c.fetchall()
        facultyNumbers = []
        for i in range(0, len(dbFacultyNumbers)):
            facultyNumbers.append(dbFacultyNumbers[i][1])
        returnValue = []
        for i in range(0, len(self._faculties)):
            if self._faculties[i].get_id() in facultyNumbers:
                returnValue.append(self._faculties[i])
        return returnValue
    def _select_dept_courses(self, deptName):
        self._c.execute("SELECT * FROM dept_course where name == '" + deptName + "'")
        dbCourseNumbers = self._c.fetchall()
        courseNumbers = []
        for i in range(0, len(dbCourseNumbers)):
            courseNumbers.append(dbCourseNumbers[i][1])
        returnValue = []
        for i in range(0, len(self._courses)):
            if self._courses[i].get_number() in courseNumbers:
                returnValue.append(self._courses[i])
        return returnValue
    def get_rooms(self): return self._rooms
    def get_faculties(self): return self._faculties
    def get_courses(self): return self._courses
    def get_depts(self): return self._depts
    def get_timings(self): return self._timings
    def get_numberOfClasses(self): return self._numberOfClasses

class Schedule:
    def __init__(self):
        self._data = dbMgr
        self._classes = []
        self._conflicts = []
        self._fitness = -1
        self._classNumb = 0
        self._isFitnessChanged = True
    def get_classes(self):
        self._isFitnessChanged = True
        return self._classes
    def get_conflicts(self): return self._conflicts
    def get_fitness(self):
        if (self._isFitnessChanged == True): # Fitness is changed but not updated
            self._fitness = self.calculate_fitness()
            self._isFitnessChanged = False
        return self._fitness
    def initialize(self):
        depts = self._data.get_depts()
        for i in range(0, len(depts)):
            courses = depts[i].get_courses()
            for j in range(0, len(courses)):
                newClass = Class(self._classNumb, depts[i], courses[j])
                self._classNumb += 1
                newClass.set_timing(dbMgr.get_timings()[rnd.randrange(0, len(dbMgr.get_timings()))])
                newClass.set_room(dbMgr.get_rooms()[rnd.randrange(0, len(dbMgr.get_rooms()))])
                newClass.set_faculty(courses[j].get_faculties()[rnd.randrange(0, len(courses[j].get_faculties()))])
                self._classes.append(newClass)
        return self
    def calculate_fitness(self):
        self._conflicts = []
        classes = self.get_classes()
        for i in range(0, len(classes)):
            seatingCapacityConflict = list()
            seatingCapacityConflict.append(classes[i])
            if (classes[i].get_room().get_seatingCapacity() < classes[i].get_course().get_maxNumOfStudents()): # Conflict 1: Seating Capacity
                self._conflicts.append(Conflict(Conflict.ConflictType.NUMB_OF_STUDENTS, seatingCapacityConflict))
            if (classes[i].get_timing() not in classes[i].get_faculty().get_availability()):
                conflictBetweenClasses = list()
                conflictBetweenClasses.append(classes[i])
                self._conflicts.append(Conflict(Conflict.ConflictType.FACULTY_AVAILABILITY, conflictBetweenClasses)) # C2: Not preferred time
            for j in range(i, len(classes)):
                if (classes[i].get_timing() == classes[j].get_timing() and classes[i].get_id() != classes[j].get_id()):
                    if (classes[i].get_room() == classes[j].get_room()):
                        roomBookingConflict = list()
                        roomBookingConflict.append(classes[i])
                        roomBookingConflict.append(classes[j])
                        self._conflicts.append(Conflict(Conflict.ConflictType.ROOM_BOOKING, roomBookingConflict)) # C3: Classes in same room
                    if (classes[i].get_faculty() == classes[j].get_faculty()):
                        facultyBookingConflict = list()
                        facultyBookingConflict.append(classes[i])
                        facultyBookingConflict.append(classes[j])
                        self._conflicts.append(Conflict(Conflict.ConflictType.FACULTY_BOOKING, facultyBookingConflict)) # C4: Same faculty, same time
                if (classes[i].get_timing() == classes[j].get_timing() and
                    classes[i].get_dept() == classes[j].get_dept() and
                    classes[i].get_id() != classes[j].get_id()):
                    sameDeptSameTimeConflict = list()
                    sameDeptSameTimeConflict.append(classes[i])
                    sameDeptSameTimeConflict.append(classes[j])
                    self._conflicts.append(Conflict(Conflict.ConflictType.SAME_SLOT, sameDeptSameTimeConflict))  # C5: Classes in the same department at the same time
        return 1 / ((1.0*len(self._conflicts) + 1)) # Fitness function (as number of conflicts increases, fitness decreases)
    def __str__(self):
        returnValue = ""
        for i in range(0, len(self._classes)-1):
            returnValue += str(self._classes[i]) + ", "
        returnValue += str(self._classes[len(self._classes)-1]) # To remove ","
        return returnValue
    
class Population:
    def __init__(self, size):
        self._size = size
        self._data = dbMgr
        self._schedules = []
        for i in range(0, size):
            self._schedules.append(Schedule().initialize())
    def get_schedules(self): return self._schedules

class GeneticAlgorithm:
    def evolve(self, population): return self._mutate_population(self._crossover_population(population))
    
    def _crossover_population(self, pop):
        crossover_pop = Population(0)
        for i in range(NUMB_OF_ELITE_SCHEDULES):
            crossover_pop.get_schedules().append(pop.get_schedules()[i])
        i = NUMB_OF_ELITE_SCHEDULES
        while i < POPULATION_SIZE:
            schedule1 = self._select_tournament_population(pop).get_schedules()[0]
            schedule2 = self._select_tournament_population(pop).get_schedules()[0]
            crossover_pop.get_schedules().append(self._crossover_schedule(schedule1, schedule2))
            i += 1
        return crossover_pop

    def _mutate_population(self, population):
        for i in range(NUMB_OF_ELITE_SCHEDULES, POPULATION_SIZE):
            self._mutate_schedule(population.get_schedules()[i])
        return population

    def _crossover_schedule(self, schedule1, schedule2):
        crossoverSchedule = Schedule().initialize()
        for i in range(0, len(crossoverSchedule.get_classes())):
            if(rnd.random() > 0.5):
                crossoverSchedule.get_classes()[i] = schedule1.get_classes()[i]
            else:
                crossoverSchedule.get_classes()[i] = schedule2.get_classes()[i]
        return crossoverSchedule

    def _mutate_schedule(self, mutateSchedule):
        '''To be called by _mutate_population'''
        schedule = Schedule().initialize()
        for i in range(0, len(mutateSchedule.get_classes())):
            if (MUTATION_RATE > rnd.random()): mutateSchedule.get_classes()[i] = schedule.get_classes()[i]
        return mutateSchedule

    def _select_tournament_population(self, pop): # Selecting fittest out of TOURNAMENT_SELECTION_SIZE(3) randomly chosen schedules
        tournament_pop = Population(0)
        i = 0
        while i < TOURNAMENT_SELECTION_SIZE:
            tournament_pop.get_schedules().append(pop.get_schedules()[rnd.randrange(0, POPULATION_SIZE)])
            i += 1
        tournament_pop.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
        return tournament_pop

class Course:
    def __init__(self, number, name, faculties, maxNumOfStudents):
        self._number = number # Variable _name is convention to convey that variable is private
        self._name = name
        self._faculties = faculties
        self._maxNumOfStudents = maxNumOfStudents
    def get_number(self): return self._number
    def get_name(self): return self._name
    def get_faculties(self): return self._faculties
    def get_maxNumOfStudents(self): return self._maxNumOfStudents
    def __str__(self): return self._name # If an object is printed, then its name is shown
    
class Faculty:
    def __init__(self, id, name, availability):
        self._id = id
        self._name = name
        self._availability = availability
    def get_id(self): return self._id
    def get_name(self): return self._name
    def get_availability(self): return self._availability
    def __str__(self): return self._name

class Room:
    def __init__(self, number, seatingCapacity):
        self._number = number
        self._seatingCapacity = seatingCapacity
    def get_number(self): return self._number
    def get_seatingCapacity(self): return self._seatingCapacity

class Timing:
    def __init__(self, id, time):
        self._id = id
        self._time = time
    def get_id(self): return self._id
    def get_time(self): return self._time

class Department:
    def __init__(self, name, courses):
        self._name = name
        self._courses = courses
    def get_name(self): return self._name
    def get_courses(self): return self._courses

class Class:
    def __init__(self, id, dept, course):
        self._id = id
        self._dept = dept
        self._course = course
        self._faculty = None
        self._timing = None
        self._room = None
    def get_id(self): return self._id
    def get_dept(self): return self._dept
    def get_course(self): return self._course
    def get_faculty(self): return self._faculty
    def get_timing(self): return self._timing
    def get_room(self): return self._room
    def set_faculty(self, faculty): self._faculty = faculty 
    def set_timing(self, timing): self._timing = timing 
    def set_room(self, room): self._room = room 
    def __str__(self):
        return str(self._dept.get_name()) + "," + str(self._course.get_number()) + "," + \
               str(self._room.get_number()) + "," + str(self._faculty.get_id()) + "," + str(self._timing.get_id())

class Conflict:
    class ConflictType(Enum):
        FACULTY_BOOKING = 1
        ROOM_BOOKING = 2
        NUMB_OF_STUDENTS = 3
        FACULTY_AVAILABILITY = 4
        SAME_SLOT = 5
    def __init__(self, conflictType, conflictBetweenClasses):
        self._conflictType = conflictType
        self._conflictBetweenClasses = conflictBetweenClasses
    def get_conflictType(self): return self._conflictType
    def get_conflictBetweenClasses(self): return self._conflictBetweenClasses
    def __str__(self): return str(self._conflictType)+" "+str(" and ".join(map(str, self._conflictBetweenClasses)))

class DisplayMgr:
    def print_available_data(self):
        print("> All Available Data")
        self.print_dept()
        self.print_course()
        self.print_room( )
        self.print_faculty()
        self.print_timings()
    def print_dept(self):
        depts = dbMgr.get_depts()
        availableDeptsTable = prettytable.PrettyTable(['dept', 'courses'])
        for i in range(0, len(depts)):
            courses = depts.__getitem__(i).get_courses()
            tempStr = "["
            for j in range(0, len(courses) - 1):
                tempStr += courses[j].__str__() +", "
            tempStr += courses[len(courses) - 1].__str__() + "]"
            availableDeptsTable.add_row([depts.__getitem__(i).get_name(), tempStr])
        print(availableDeptsTable)
    def print_course(self):
        availableCoursesTable = prettytable.PrettyTable(['id', 'course #', 'max # of students', 'faculties'])
        courses = dbMgr.get_courses()
        for i in range(0, len(courses)):
            faculties = courses[i].get_faculties()
            tempStr = ""
            for j in range(0, len(faculties) - 1):
                tempStr += faculties[j].__str__() + ", "
            tempStr += faculties[len(faculties) - 1].__str__()
            availableCoursesTable.add_row(
                [courses[i].get_number(), courses[i].get_name(), str(courses[i].get_maxNumOfStudents()), tempStr])
        print(availableCoursesTable)
    def print_faculty(self):
        availableFacultiesTable = prettytable.PrettyTable(['id', 'faculty', 'availability'])
        faculties = dbMgr.get_faculties()
        for i in range(0, len(faculties)):
            availability = []
            for j in range(0, len(faculties[i].get_availability())):
                availability.append(faculties[i].get_availability()[j].get_id())
            availableFacultiesTable.add_row([faculties[i].get_id(), faculties[i].get_name(), availability])
        print(availableFacultiesTable)
    def print_room(self):
        availableRoomsTable = prettytable.PrettyTable(['room #', 'max seating capacity'])
        rooms = dbMgr.get_rooms()
        for i in range(0, len(rooms)):
            availableRoomsTable.add_row([str(rooms[i].get_number()), str(rooms[i].get_seatingCapacity())])
        print(availableRoomsTable)
    def print_timings(self):
        availableMeetingTimeTable = prettytable.PrettyTable(['id', 'Meeting Time'])
        timings = dbMgr.get_timings()
        for i in range(0, len(timings)):
            availableMeetingTimeTable.add_row([timings[i].get_id(), timings[i].get_time()])
        print(availableMeetingTimeTable)
    def print_generation(self, population):
        tablel = prettytable.PrettyTable(['schedule #', 'fitness', '# of conflicts', 'classes [dept,class,room,faculty,timing]'])
        schedules = population.get_schedules()
        for i in range(0, len(schedules)):
            tablel.add_row([str(i+1), round(schedules[i].get_fitness(),3), len(schedules[i].get_conflicts()), schedules[i].__str__()])
        print(tablel)
    def print_schedule_as_table(self, schedule):
        classes = schedule.get_classes()
        data = {'Class #': [], 'Dept': [], 'Course': [], 'Room': [], 'Faculty': [], 'Timing': []}

        for i in range(len(classes)):
            data['Class #'].append(i + 1)
            data['Dept'].append(classes[i].get_dept().get_name())
            course_info = f"{classes[i].get_course().get_name()} ({classes[i].get_course().get_number()}, {classes[i].get_course().get_maxNumOfStudents()})"
            data['Course'].append(course_info)
            room_info = f"{classes[i].get_room().get_number()} ({classes[i].get_room().get_seatingCapacity()})"
            data['Room'].append(room_info)
            faculty_info = f"{classes[i].get_faculty().get_name()} ({classes[i].get_faculty().get_id()})"
            data['Faculty'].append(faculty_info)
            timing_info = f"{classes[i].get_timing().get_time()} ({classes[i].get_timing().get_id()})"
            data['Timing'].append(timing_info)

        return pd.DataFrame(data)


app = Flask(__name__)

# Function to process and insert data into SQLite database
def process_and_insert_data(file_path):
    # Connect to SQLite3 database
    conn = sql.connect('class_schedule.db')
    c = conn.cursor()

    # Read data from Excel sheets including the first row
    df_room = pd.read_excel(file_path, sheet_name='room')
    df_timing = pd.read_excel(file_path, sheet_name='timing')
    df_faculty = pd.read_excel(file_path, sheet_name='faculty')
    df_faculty_availability = pd.read_excel(file_path, sheet_name='faculty_availability')
    df_course_faculty = pd.read_excel(file_path, sheet_name='course_faculty')
    df_course = pd.read_excel(file_path, sheet_name='course')
    df_dept = pd.read_excel(file_path, sheet_name='dept')
    df_dept_course = pd.read_excel(file_path, sheet_name='dept_course')

    # Create tables and insert data
    df_room.to_sql('room', conn, index=False, if_exists='replace')
    df_timing.to_sql('timing', conn, index=False, if_exists='replace')
    df_faculty.to_sql('faculty', conn, index=False, if_exists='replace')

    # Process faculty_availability associations
    df_faculty_availability_expanded = df_faculty_availability.assign(timing_id=df_faculty_availability['timing_id'].str.split(',')).explode('timing_id')
    df_faculty_availability_expanded.to_sql('faculty_availability', conn, index=False, if_exists='replace')

    df_course.to_sql('course', conn, index=False, if_exists='replace')
    df_dept.to_sql('dept', conn, index=False, if_exists='replace')

    # Process course_faculty associations
    df_course_faculty_expanded = df_course_faculty.assign(faculty_number=df_course_faculty['faculty_number'].str.split(',')).explode('faculty_number')
    df_course_faculty_expanded.to_sql('course_faculty', conn, index=False, if_exists='replace')

    # Process dept_course associations
    df_dept_course_expanded = df_dept_course.assign(course_numb=df_dept_course['course_numb'].str.split(',')).explode('course_numb')
    df_dept_course_expanded.to_sql('dept_course', conn, index=False, if_exists='replace')

    # Commit changes and close connection
    conn.commit()
    c.close()
    conn.close()

# Route for home page
@app.route('/')
def home_page():
    return render_template("index.html")

# Route for about page
@app.route('/about')
def about_page():
    return render_template("about.html")

# Route for uploading a file
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an empty file without a filename
        if file.filename == '':
            return redirect(request.url)
        if file:
            # Save the file to a secure location
            file_path = os.path.join('uploads', file.filename)
            file.save(file_path)
            
            # Process and insert data into the database
            process_and_insert_data(file_path)
            
            # Generate timetable
            generate_timetable(file_path)

            return render_template('download.html')
    
    return render_template('upload.html')

def generate_timetable(file_path):
    global dbMgr
    global displayMgr
    global population
    global geneticAlgorithm

    # Load the database with the uploaded file
    process_and_insert_data(file_path)

    # Re-initialize the Display Manager and Population
    dbMgr = DBMgr()
    displayMgr = DisplayMgr()
    population = Population(POPULATION_SIZE)
    geneticAlgorithm = GeneticAlgorithm()
    population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)

    # Run the genetic algorithm to generate the timetable
    generationNumber = 0
    while population.get_schedules()[0].get_fitness() != 1.0:
        generationNumber += 1
        population = geneticAlgorithm.evolve(population)
        population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)

    # Export the generated timetable to an Excel file
    excel_file_path = 'generated_schedule_output.xlsx'
    displayMgr.print_schedule_as_table(population.get_schedules()[0]).to_excel(excel_file_path, index=False)

@app.route('/download')
def download_file():
    return send_file('generated_schedule_output.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
