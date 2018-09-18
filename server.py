
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@35.227.79.146/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@35.227.79.146/proj1part2"
#
DATABASEURI = "postgresql://sz2699:7790@35.227.79.146/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
# engine.execute("""CREATE TABLE IF NOT EXISTS test (
#   id serial,
#   name text
# );""")
cursor = engine.execute("""SELECT mname, degree from majors_and_affiliation ORDER BY mname;""")
majors = []
for result in cursor:
  majors.append(result[0].replace(" ", "_")+'$'+result[1])
cursor.close()

cursor = engine.execute("""SELECT pname from professors ORDER BY pname;""")
profs = []
for result in cursor:
  profs.append(result['pname'].replace(" ", "_"))
cursor.close()

cursor = engine.execute("""SELECT dname from departments_and_head ORDER BY dname;""")
dept_names = []
for result in cursor:
  dept_names.append(result['dname'])
cursor.close()

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print(request.args)

  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html", data = majors, data2 = profs)
  # return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at:
# 
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#
@app.route('/another')
def another():
  return render_template("another.html", data0 = dept_names)


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  # get data from index.html
  sname = request.form['sname']
  college = request.form['college']
  uni = request.form['uni']
  sid = request.form['sid']
  major = request.form['major'].split('$')
  mname = major[0].replace("_", " ")
  degree = major[1].replace("_", " ")
  advisor = request.form['advisor'].replace("_", " ")
  until = request.form['until']
  since = request.form['since']

  if uni == '' or mname == '' or degree == '' or until == '' or since == '':
    return ("Please enter all required fields")

  if len(uni) > 8 or len(sid) > 10 or len(sname) > 30 or len(college) > 8:
    return ("Please check your information")

  if int(until) <= 2000 or int(since) <= 2000 or int(until) < int(since):
    return ("Please double check your enrollment years")

  # avoid duplicate primary/candicate key value in students table
  cursor = g.conn.execute('SELECT uni, sid FROM students')
  existing_unis = []
  existing_sids = []
  for result in cursor:
     existing_unis.append(result['uni'])
     existing_sids.append(result['sid'])
  cursor.close()

  # insertion to students table
  if uni not in existing_unis and sid not in existing_sids:
    g.conn.execute('INSERT INTO students VALUES (%s, %s, %s, %s)', college, sname, uni, sid)
  else:
    print("Duplicate in students table. Not inserted")

  # avoid duplicate primary key value in pursuing table
  cursor = g.conn.execute('SELECT uni, mname, degree FROM pursuing')
  existing_umd = []
  for result in cursor:
     existing_umd.append((result['uni'], result['mname'], result['degree']))
  cursor.close()

  # insertion to pursuing table
  if (uni, mname, degree) not in existing_umd:
    g.conn.execute('INSERT INTO pursuing VALUES (%s, %s, %s, %s, %s)', uni, mname, degree, until, since)
  else:
    print("Duplicate in pursuing table. Not inserted")

  # avoid duplicate primary key value in advised_by table
  cursor = g.conn.execute('SELECT A.uni, P.pname FROM advised_by A, professors P WHERE A.email = P.email')
  existing_ue = []
  for result in cursor:
     existing_ue.append((result['uni'], result['pname']))
  cursor.close()

  # insertion to advised_by table
  if advisor != '' and (uni, advisor) not in existing_ue:
    cursor = g.conn.execute("SELECT email FROM professors WHERE pname = %s", advisor)
    emails = []
    for result in cursor:
      emails.append(result['email'])
    cursor.close()
    if len(emails) == 0:
      return ("Your advisor in not in the database")
    g.conn.execute('INSERT INTO advised_by VALUES (%s, %s)', uni, emails[0])
  else:
    print("Duplicate in advised_by table. Not inserted")

  # display course info for a given major
  cursor = g.conn.execute("SELECT C.cid, C.cname, P.pname, R.type_of_course, C.credits FROM requires R, courses C, taught_by T, professors P WHERE R.cid = C.cid AND R.cid = T.cid AND T.email = P.email AND R.mname = %s", mname)
  entries = [dict(id=result[0], name=result[1], prof=result[2], typ=result[3], cred=result[4]) for result in cursor.fetchall()]
  cursor.close()

  # get total credits
  cursor = g.conn.execute("SELECT total_credits FROM majors_and_affiliation WHERE mname = %s", mname)
  cred = []
  for result in cursor:
    cred.append(result['total_credits'])
  cursor.close()

  return render_template("courses.html", major = mname, data = entries, credits = cred, uni = uni)

@app.route('/add2',methods=['POST'])
def add2():

  # add tuple to taken table
  unis = request.form.getlist('uni')
  cids = request.form.getlist('cid')
  terms = request.form.getlist('term')

  cursor = g.conn.execute('SELECT cid FROM courses')
  existing_cids = []
  for result in cursor:
    existing_cids.append(result['cid'])
  cursor.close()

  cursor = g.conn.execute('SELECT cid, uni FROM taken')
  existing_courses_taken = []
  for result in cursor:
    existing_courses_taken.append((result['cid'], result['uni']))
  cursor.close()  

  cursor = g.conn.execute('SELECT uni FROM students')
  existing_unis = []
  for result in cursor:
    existing_unis.append(result['uni'])
  cursor.close()

  for i in range(len(unis)):
    if terms[i] != '' and unis[i] != '' and cids[i] != '':
      if len(unis[i]) > 8 or len(cids[i]) > 15 or len(terms[i]) > 12:
        return ("Please check your input")

      # check for existance of cid
      if unis[i] in existing_unis and cids[i] in existing_cids and (cids[i], unis[i]) not in existing_courses_taken:
        g.conn.execute('INSERT INTO taken VALUES (%s, %s, %s)', terms[i], unis[i], cids[i])
        return render_template("success.html")
      else:
          return ("Please check your input")
    elif terms[i] == '' and unis[i] != '' and cids[i] != '':
      return ("Please fill all entries on a single line")
    elif terms[i] != '' and unis[i] == '' and cids[i] != '':
      return ("Please fill all entries on a single line")
    elif terms[i] != '' and unis[i] != '' and cids[i] == '':
      return ("Please fill all entries on a single line")
    elif terms[i] == '' and unis[i] == '' and cids[i] != '':
      return ("Please fill all entries on a single line")
    elif terms[i] == '' and unis[i] != '' and cids[i] == '':
      return ("Please fill all entries on a single line")
    elif terms[i] != '' and unis[i] == '' and cids[i] == '':
      return ("Please fill all entries on a single line")


@app.route('/search', methods=['POST'])
def search():
  dname = request.form['dname']

  # get majors that the department offers
  if dname != '':
    cursor = g.conn.execute('SELECT mname FROM majors_and_affiliation WHERE dname = %s', dname)
    mnames = []
    for result in cursor:
      mnames.append(result['mname'])
    cursor.close()

    context = dict(data = mnames)



    # get professors in the deparment
    cursor = g.conn.execute('SELECT P.pname, P.email, P.office_location, P.office_hour FROM is_in I, professors P WHERE I.email = P.email AND I.dname = %s', dname)
    profs_in_dept = [dict(name=result[0], email=result[1], loc=result[2], oh=result[3]) for result in cursor.fetchall()]
    cursor.close()

    # get department head
    cursor = g.conn.execute('SELECT P.pname, P.email, D.since, D.location, D.subject FROM departments_and_head D, professors P WHERE D.email = P.email AND D.dname = %s', dname)
    heads = [dict(name=result[0], email=result[1], since=result[2], loc=result[3], subj=result[4]) for result in cursor.fetchall()]
    cursor.close()

    return render_template("another.html", data0 = dept_names, data1 = mnames, data2 = profs_in_dept, data3 = heads, data4 = [dname])

  else:
    return render_template("err.html")


@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()