from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from email_validator import validate_email, EmailNotValidError
from functools import wraps

##############################FORM-CLASS#############################################
#KULLANICI KAYIT FORMU
class RegisterForm(Form):
    name = StringField("Adınız ve Soyadınız", validators=[validators.length(min=4, max=25)])
    username = StringField("Kullanıcı Adınız", validators=[validators.length(min=5, max=15)])
    email = StringField("E-posta Adresi", validators=[])
    # Yukarıda validators için boş bir liste bıraktık, çünkü e-posta doğrulama kısmını kendimiz yapacağız
    password = PasswordField("Parolanızı Girin", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin!"),
        validators.EqualTo(fieldname="confirm", message="Parolanız Uyuşmuyor!")
    ])
    confirm = PasswordField("Parolanızı Tekrar Girin")
#KULLANICI GİRİŞ FORMU#################################################################
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")



##################################################
app = Flask(__name__)
app.secret_key = "fuyublog"


app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "fuyublog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)
#################################################

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")
#Kayıt Olma
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        try:
            validate_email(email)  # E-posta doğrulaması
        except EmailNotValidError as e:
            flash("Geçerli bir e-posta adresi girin.", "danger")
            return render_template("register.html", form=form)

        cursor = mysql.connection.cursor()
        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash("Tebrikler! Başarıyla kayıt oldunuz..", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)
    

#####################Girişyap##############################
@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "Select * From users where username = %s"

        result = cursor.execute(sorgu,(username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla Giriş Yaptınız!","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Hatalı Parola!","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle Bir Kullanıcı Bulunamadı!","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form=form)
#################################################################
#KULLANICI GİRİŞ YAPMA DEKORU
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","danger")
            return redirect(url_for("login"))
    return decorated_function

#####ÇıkışYap#####
@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla Çıkış Yaptınız","success")
    return redirect(url_for("index"))

######Dashboard#######
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From posts where author = %s"
    result = cursor.execute(sorgu,(session["username"],))
    if result > 0:
        myposts = cursor.fetchall()
        return render_template("dashboard.html", myposts = myposts)
    else:
        return render_template("dashboard.html")


####################################
#GÖNDERİ EKLE
@app.route("/sharepost", methods = ["GET","POST"])
def sharepost():
    form = PostForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "Insert into posts(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu, (title, session["username"], content))
        mysql.connection.commit()
        cursor.close()
        flash("✔️ Tebrikler! Gönderi Paylaşıldı", "success")
        return redirect(url_for("dashboard"))


    return render_template("sharepost.html", form = form)

########GÖNDERİFORM##############
class PostForm(Form):
    title = StringField("Başlık")
    content = TextAreaField("İçerik")
    author = StringField("Yazar")
    
##################################
#Gönderi Sayfası
@app.route("/posts")
def seeposts():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From posts"
    result = cursor.execute(sorgu)
    if result > 0:
        allposts = cursor.fetchall()
        return render_template("allpost.html", allposts = allposts)
    else:
        return render_template("allposts.html")


##Gönderi Silme
@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    mysql.connection.commit()
    cursor.close()
    flash("✔️ Gönderi silindi.", "success")
    return redirect("/dashboard")
##Gönderi Düzenle
@app.route("/edit_post/<int:post_id>")
def edit_post(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()
    cursor.close()
    return render_template("edit_post.html", post=post)
##Gönderi Güncelleme
@app.route("/update_post/<int:post_id>", methods=["POST"])
def update_post(post_id):
    if request.method == "POST":
        new_title = request.form.get("title")
        new_content = request.form.get("content")

        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE posts SET title = %s, content = %s WHERE id = %s", (new_title, new_content, post_id))
        mysql.connection.commit()
        cursor.close()
        flash("✔️ Gönderi güncellendi.", "success")
        return redirect("/dashboard")
    else:
        # Düzenleme formunu göster
        return render_template("edit_post.html")


#ARAMA URL#
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        # Veritabanında arama yapacak sorguyu oluşturun
        sorgu = "SELECT * FROM posts WHERE title LIKE %s"
        keyword_with_wildcards = f"%{keyword}%"  # Arama için joker karakterler ekleyin
        result = cursor.execute(sorgu, (keyword_with_wildcards,))

        if result == 0:
            flash("Aranan kelimeye uygun içerik bulunamadı!", "warning")
            return redirect(url_for("seeposts"))
        else:
            # Bulunan gönderileri alın
            found_posts = cursor.fetchall()
            cursor.close()
            return render_template("search_results.html", found_posts=found_posts, keyword=keyword)
        


    return redirect(url_for("seeposts"))
























if __name__ == "__main__":
    app.run(debug=True)
