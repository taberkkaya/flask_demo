from flask import Flask, flash,render_template,redirect,url_for,session,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("you must login","danger")
            return redirect(url_for("login"))
    return decorated_function

class RegisterForm(Form):
    username = StringField("username",validators=[validators.length(min=5,max=25)])
    name = StringField("name",validators=[validators.length(min=5,max=25)])
    password = PasswordField("password",validators=[
        validators.data_required(),
        validators.EqualTo(fieldname="conf_pass")
    ])
    conf_pass = PasswordField("confirm password")
    email = StringField("email",validators=[validators.Email()])

class LoginForm(Form):
    username = StringField("username")
    password = PasswordField("password")

class ArticleForm(Form):
    title = StringField("title",validators=[validators.data_required()])
    content = TextAreaField("content",validators=[validators.data_required()])

app = Flask(__name__)

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "flask_demo"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
app.config["SECRET_KEY"] = "secret"

mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles",methods=["GET"])
@login_required
def articles():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(query,(session["username"],))

    if result:
        articles = cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        flash("there is no article","danger")
        redirect(url_for("addarticle"))

    return render_template("articles.html")

@app.route("/register",methods=["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate:
        name = form.name.data
        username = form.username.data
        password = sha256_crypt.encrypt(form.password.data)
        email = form.email.data

        cursor = mysql.connection.cursor()
        query = "INSERT INTO users(name,username,password,email) VALUES(%s,%s,%s,%s)"

        cursor.execute(query,(name,username,password,email))
        mysql.connection.commit()

        cursor.close()

        flash("registration successful","success")
        
        return redirect(url_for("login"))

    else:
        return render_template("register.html",form=form)

@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        query = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(query,(username,))
    
        if result:
            data = cursor.fetchone()
            real_pass = data["password"]
            
            if sha256_crypt.verify(password_entered,real_pass):
                session["logged_in"] = True
                session["username"] = username

                flash("login successful","success")
                return redirect(url_for("index"))

            else:
                flash("password is incorrect","danger")

        else:
            flash("this username connot be found","danger")
            return redirect(url_for("login"))

    else:
        return render_template("login.html",form=form)

@app.route("/logout")
def logout():
    session.clear()
    
    return redirect(url_for("index"))

@app.route("/addarticle",methods=["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate:
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        query = "INSERT INTO articles(author,title,content) VALUES(%s,%s,%s)"
        cursor.execute(query,(session["username"],title,content))

        mysql.connection.commit()
        cursor.close()

        flash("article saved","success")
        return redirect(url_for("articles"))

    return render_template("addarticle.html",form=form)

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(query,(session["username"],))

    if result:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        flash("the author has no articles","danger")
        return render_template("dashboard.html")

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(query,(id,))

    if result:
        query = "DELETE FROM articles WHERE id = %s"
        cursor.execute(query,(id,))
        mysql.connection.commit()
        cursor.close()
        flash("article deleted","danger")
        return redirect(url_for("dashboard"))
    else:
        flash("there is no article with this id","danger")
        return redirect(url_for("dashboard"))


@app.route("/detail/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(query,(id,))

    if result:
        article = cursor.fetchone()
        return render_template("detail.html",article=article)

    else:
        flash("there is no article with this id","danger")
        return render_template("detail.html")


@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE id = %s and author = %s"
        result = cursor.execute(query,(id,session["username"]))

        if result:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("edit.html",form=form)

        else:
            flash("there is no such article or you do not have permission for this action","danger")
            return redirect(url_for("index"))
    else:
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        cursor = mysql.connection.cursor()
        query = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor.execute(query,(newTitle,newContent,id))
        mysql.connection.commit()
        cursor.close()
        flash("article updated","success")
        return redirect(url_for("dashboard"))

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))

    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM articles WHERE title LIKE '%"+keyword+"%'"
        result = cursor.execute(query)

        if result:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)
        else:
            flash("the searched article was not found.","info")
            return redirect(url_for("articles"))

if __name__ == "__main__":
    app.run(debug=True)
    