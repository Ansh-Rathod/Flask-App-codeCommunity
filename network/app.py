import requests
from flask import *
from flask_mysqldb import *
from wtforms import *
from passlib.hash import sha256_crypt
from functools import WRAPPER_ASSIGNMENTS, wraps
import os
from werkzeug.utils import*


app=Flask(__name__,template_folder='./Templetes')

app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='myflaskapp'
app.config['MYSQL_CURSORCLASS']='DictCursor'

mysql=MySQL(app)

app.config['IMAGES_UPLOADS']='static/images/'
app.config['ALLOWED_IMAGE_EXTENSIONS']=['PNG','JPG','JPEG','GIF','']
def allowed(filename):
    if not "." in filename:
        return False
    ext = filename.rsplit('.',1)[1]
    if ext.upper() in app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return True
    else:
        return False
    
@app.route('/')
def index():
    return render_template('index.html')
@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                 endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


class signupform(Form):
    name=StringField('Name With Surname',[validators.Length(min=3,max=30)])
    username=StringField('Username',[validators.Length(min=5,max=10)])
    email=StringField('email',[validators.Length(min=6,max=30)])
    password=PasswordField('Password',[
        validators.Length(min=6,max=10)
        ,validators.DataRequired()
        ,validators.EqualTo('confrim',message="Please enter password and confirm password same")
        ])
    confrim=PasswordField('Confirm Password')
class loginForm(Form):
    login_username=StringField('Username',[validators.DataRequired()])
    login_password=PasswordField('Password',[validators.DataRequired()])
@app.route('/login',methods=['POST','GET'])
def login():
    login_form=loginForm(request.form)
    if request.method == 'POST' and login_form.validate():
        login_username=login_form.login_username.data
        login_password=login_form.login_password.data
        cur=mysql.connection.cursor()
        result=cur.execute("SELECT * FROM users WHERE _username =%s",[login_username])
        if result>0:
            data=cur.fetchone()
            password=data['_password']
            if sha256_crypt.verify(login_password,password):
                session['logged_in']=True
                session['name']=data['_name']
                session['li_username']=data['_username']
                session['profile']=data['_profile']
                flash('hi,'+session['name']+'! you are Logged in','success')
                return redirect(url_for('home'))
            else:
                flash('Your Passwowrd is Incorrect','danger')
                return redirect(url_for('login'))
        else:
            flash('Invaild Password or username',"danger")
            return redirect(url_for('login'))
    return render_template('login.html',login_form=login_form)

            
@app.route('/signup',methods=['POST','GET'])
def singup():
    form=signupform(request.form)
    if request.method == 'POST' and form.validate():
        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(str(form.password.data))
        cur=mysql.connection.cursor()
        cur.execute("INSERT INTO users (_name,_username,_email,_password,_profile,_fullname,_about) VALUES (%s,%s,%s,%s,'user.png','','')",(name,username,email,password))
        mysql.connection.commit()
        cur.close()
        flash("You Successfully SignUp and Now You Can Login","success")
        
        return redirect(url_for('index'))
    return render_template('signup.html',form=form)

def is_logged_in(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unathorised please login','danger')
            return redirect(url_for('login'))
    return wrapper
@app.route('/home',methods=['POST','GET'])
@is_logged_in
def home():
    cur=mysql.connection.cursor()
    data=cur.execute('SELECT * FROM users WHERE _username=%s',[session['li_username']])
    result=cur.fetchone()
    session['username']=result['_username']
    mysql.connection.commit()
    cur.close()
    
    cur1=mysql.connection.cursor()
    data1=cur1.execute('SELECT * FROM articals order by created_date DESC')
    result1=cur1.fetchall()
    mysql.connection.commit()
    cur1.close()
    return render_template('home.html',results=result1)
@app.route('/logout')
def logout():
    session.clear()
    flash('you are logged out','success')
    return redirect(url_for('login'))
@app.route('/search',methods=['POST','GET'])
def search():
    cur1=mysql.connection.cursor()
    data1=cur1.execute('SELECT * FROM users')
    result1=cur1.fetchall()
    mysql.connection.commit()
    cur1.close()
    if request.method == 'POST':
        username=request.form['search']
        cur=mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE _username LIKE %s",[username])
        result=cur1.fetchall()
        
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('search',Sresult=result))
    
    return render_template('search.html',result1=result1)
@app.route('/profile')
def profile():
    cur=mysql.connection.cursor()
    data=cur.execute('SELECT * FROM users WHERE _username=%s',[session['username']])
    
    result=cur.fetchone()
    
    profile=result['_profile']
    name=result['_name']
    about=result['_about']
    mysql.connection.commit()
    cur.close()  
    cur1=mysql.connection.cursor()
    data1=cur1.execute('SELECT * FROM articals WHERE qi_name=%s',[session['username']])
    result1=cur1.fetchall()
    mysql.connection.commit()
    cur1.close()
    

    
    return render_template('profile.html',profile=profile,name=name,about=about,questions=result1)


@app.route('/updateprofile',methods=['POST','GET'])
def updateprofile():
    cur=mysql.connection.cursor()
    data=cur.execute('SELECT * FROM users WHERE _username=%s',[session['username']])
    result=cur.fetchone()
    profile=result['_profile']
    mysql.connection.commit()
    cur.close()
    if request.method =='POST':

        if request.files:
            image=request.files['image']
            
            if not allowed(image.filename):
                flash('please Select any image','danger')
                return redirect(url_for('updateprofile'))
            else: 
                filename=secure_filename(image.filename)
                session['secure_filename']=True
                session['filename']=filename
                # print(session['filename'])
                cur=mysql.connection.cursor()
                cur.execute("UPDATE users SET _profile = %s WHERE _username = %s",(session['filename'],session['username']))
                mysql.connection.commit()
                cur.close()
                flash('your Profile updated','success')
                
                image.save(os.path.join(app.config['IMAGES_UPLOADS'],filename))
                return redirect(url_for('profile'))
        if request.method == 'POST':
             fullname=request.form['fullname']
             about=request.form['about']
             cur=mysql.connection.cursor()
             cur.execute("UPDATE users SET _fullname = %s ,_about =%s WHERE _username = %s",(fullname,about,session['username']))
             mysql.connection.commit()
             cur.close()
             flash('success','success')
             return redirect(url_for('profile'))
             
        
    return render_template('updateprofile.html',profile=profile)

@app.route('/setting',methods=['POST','GET'])
def settings():
    cur=mysql.connection.cursor()
    data=cur.execute('SELECT * FROM users WHERE _username=%s',[session['username']])
    result=cur.fetchone()
    li_name=result['_name']
    li_username=result['_username']
    li_password=result['_password']
    li_email=result['_email']
    profile=result['_profile']
    mysql.connection.commit()
    cur.close()
    form=signupform(request.form)
    if request.method == 'POST':
        name=form.name.data
        username=session['username']
        email=form.email.data
        cur=mysql.connection.cursor()
        cur.execute("UPDATE users SET _name = %s, _username = %s, _email = %s WHERE _username = %s",(name,username,email,session['username']))
        mysql.connection.commit()
        cur.close()
        flash("You Successfully setting up your account","success")
        
        return redirect(url_for('home'))
    
        
        
 

    return render_template('setting.html',profile=profile,name=li_name,password=li_password,username=li_username,email=li_email,form=form)

@app.route('/newpassword',methods=['POST','GET'])
def newpassword():
    cur=mysql.connection.cursor()
    data=cur.execute('SELECT * FROM users WHERE _username=%s',[session['username']])
    result=cur.fetchone()
    profile=result['_profile']
    mysql.connection.commit()
    cur.close()
    form=signupform(request.form)
    if request.method == 'POST':
        password=sha256_crypt.encrypt(str(form.password.data))
        cur=mysql.connection.cursor()
        cur.execute("UPDATE users SET _password=%s WHERE _username = %s",(password,session['username']))
        mysql.connection.commit()
        cur.close()
        flash("You Successfully update your New password","success")
        return redirect(url_for("home"))
    return render_template('newpassword.html',profile=profile,form=form)

class addpostform(Form):
    title=StringField('Title',[validators.DataRequired(),validators.Length(min=8,max=70)])
    question=TextAreaField('Add Question',[validators.DataRequired(),validators.Length(min=8,max=500)])
class addAnswerform(Form):
    Answer=TextAreaField('Add Answer',[validators.DataRequired(),validators.Length(min=8,max=500)])



@app.route('/addpost',methods=['POST','GET'])

def addpost():
    cur=mysql.connection.cursor()
    data=cur.execute('SELECT * FROM users WHERE _username=%s',[session['username']])
    result=cur.fetchone()
    profile=result['_profile']
    mysql.connection.commit()
    cur.close()
    form=addpostform(request.form)
    if request.method == 'POST':
        title=form.title.data
        qiz=form.question.data
        if request.files:
            image=request.files['image']
            
            if not allowed(image.filename):
                
                filename=''
                # print(session['filename'])
                cur=mysql.connection.cursor()
                cur.execute("INSERT INTO articals (_title, _body,qi_profile,qi_name,qi_img) VALUES (%s,%s,%s,%s,%s)",(title,qiz,profile,session['username'],filename))
                mysql.connection.commit()
                cur.close()
                flash('your Question added successfully','success')
                
                
                
                return redirect(url_for('home'))
            else: 
                filename=secure_filename(image.filename)
                session['secure_filename']=True
                
                # print(session['filename'])
                cur=mysql.connection.cursor()
                cur.execute("INSERT INTO articals (_title, _body,qi_profile,qi_name,qi_img) VALUES (%s,%s,%s,%s,%s)",(title,qiz,profile,session['username'],filename))
                mysql.connection.commit()
                cur.close()
                flash('your Question added successfully','success')
                
                image.save(os.path.join(app.config['IMAGES_UPLOADS'],filename))
                return redirect(url_for('home'))
       
    return render_template('addpost.html',profile=profile,form=form)
@app.route('/answer/<string:id>/',methods=['POST','GET'])
def answer(id):
    cur=mysql.connection.cursor()
    data=cur.execute('SELECT * FROM articals WHERE id=%s',[id])
    result=cur.fetchone()

    mysql.connection.commit()
    cur.close()
    cur1=mysql.connection.cursor()
    data1=cur1.execute('SELECT * FROM users WHERE _username=%s',[session['username']])
    result1=cur1.fetchone()
    form=addAnswerform(request.form)
    mysql.connection.commit()
    cur1.close()
    
    cur4=mysql.connection.cursor()
    data4=cur4.execute('SELECT * FROM answer WHERE qi_id=%s',[id])
    result4=cur4.fetchall()

    mysql.connection.commit()
    cur4.close()
    if request.method == 'POST':
        answer=form.Answer.data
        cur2=mysql.connection.cursor()
        cur2.execute('INSERT INTO answer(qi_id,qi_answer,qi_profile,qi_name) VALUES (%s,%s,%s,%s)',(id,answer,result1['_profile'],result1['_username']))
        mysql.connection.commit()
        cur2.close()
        return redirect(url_for('answer',id=id))

    return render_template('answer.html',id=id,result=result,result1=result1,form=form,answers=result4)

@app.route('/delete/<string:id>/',methods=['POST','GET'])
def delete(id):
    if request.method == 'POST':
        ans_id=request.form['ans_id']
        cur5=mysql.connection.cursor()
        cur5.execute('DELETE FROM answer WHERE id=%s ;',[id])

        mysql.connection.commit()
        cur5.close()
        flash('your answer is deleted', 'success')
        return redirect(url_for('home'))
@app.route('/deleteqiz/<string:id>/',methods=['POST','GET'])
def delete_qiz(id):
    if request.method == 'POST':
        
        cur5=mysql.connection.cursor()
        cur5.execute('DELETE FROM articals WHERE id=%s ;',[id])

        mysql.connection.commit()
        cur5.close()
        flash('your question was deleted', 'success')
        return redirect(url_for('home'))
@app.route('/about/<string:id>/')
def about(id):
    cur =mysql.connection.cursor()
    cur.execute('SELECT * FROM users WHERE id=%s',[id])
    result = cur.fetchone()
    mysql.connection.commit()
    cur.close()
    cur1 =mysql.connection.cursor()
    cur1.execute('SELECT * FROM articals WHERE qi_name=%s order by created_date DESC',[result['_username']])
    result1 = cur1.fetchall()
    mysql.connection.commit()
    cur1.close()
    return render_template('about.html',result=result,questions=result1)

if __name__ == '__main__':
    app.secret_key="appi00"
    app.run()

     
