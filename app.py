import datetime 
## FLASK DEFAULTS ##
from flask import Flask, render_template, request, redirect, session
from flask_session import Session
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"]="filesystem"
Session(app)
## SQL DEFAULTS ##
import sqlite3
con = sqlite3.connect("library.db", check_same_thread=False)
cur = con.cursor()


def auth_user(name, pin):
    cur.execute("SELECT COUNT(*) FROM users WHERE USERNAME=?", (name, ))
    res = cur.fetchone()
    result = res[0]
    if result == 0:
        return "No Account"
    cur.execute("SELECT PIN FROM users WHERE USERNAME=?", (name, ))
    res = cur.fetchone()
    result = res[0]
    if result != pin:
        return "Incorrect pin"
    if result == pin:
        return True
def find_book(title, author):
    cur.execute("SELECT COUNT(*) FROM books WHERE TITLE=? AND AUTHOR=?", (title, author))
    res = cur.fetchone()
    result = res[0]
    if result == 0:
        return "No Book"
    cur.execute("SELECT rowid, STATUS, BORROWER, EBOOK, EBOOK_LINK, SERIES, NUM_IN_SERIES, DUE_DATE FROM books WHERE TITLE=? AND AUTHOR=?", (title, author))
    res = cur.fetchone()
    rowid = res[0]
    status = res[1]
    borrower = res[2]
    ebook = res[3]
    ebook_link = res[4]
    series = res[5]
    series_num = res[6]
    due_date = res[7]
    return [rowid, status, borrower, ebook, ebook_link, series, series_num, due_date]
def add_book(title, author, ebook, ebook_link, status, series, series_num): 
    cur.execute("SELECT COUNT(*) FROM books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
    res = cur.fetchone()
    if res[0] == 1:
        return False

    cur.execute("INSERT INTO books (TITLE, AUTHOR, EBOOK, EBOOK_LINK, STATUS, SERIES, NUM_IN_SERIES) VALUES (?, ?, ?, ?, ?, ?, ?)", (title, author, ebook, ebook_link, status, series, series_num))
    con.commit()
    return True
def delete_book(title, author):
    cur.execute("SELECT COUNT(*) FROM books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
    res = cur.fetchone()
    if res[0] != 1:
        return False
    cur.execute("SELECT rowid FROM books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
    res = cur.fetchone()
    resfi = res[0]
    cur.execute(f"DELETE FROM books WHERE rowid = {resfi}")
    con.commit()
    return True
def checkout_book(book_id):
    username = session.get("username", False)
    if not book_id:
        return
    cur.execute("SELECT COUNT(*) FROM books WHERE rowid = ?", (book_id,))
    res = cur.fetchone()
    if res[0] == 0:
        return False
    cur.execute("SELECT STATUS FROM books WHERE rowid = ?", (book_id,))
    status = cur.fetchone()[0]
    if status != "available":
        return "Not available"
    cur.execute("SELECT rowid FROM users WHERE USERNAME = ?", (username,))
    rowid = cur.fetchone()[0]
    #  + datetime.timedelta(days=5)
    due_date = (datetime.datetime.now()).strftime('%Y-%m-%d')
    cur.execute("UPDATE books SET STATUS = 'Checked out', BORROWER = ?, DUE_DATE = ? WHERE rowid = ?", (username, due_date, book_id))
    cur.execute("INSERT INTO checked_out(UserID, BookID) VALUES (?, ?)", (rowid, book_id))
    con.commit()
    return True
def return_book(title, author):
    username = session.get("username", False)
    cur.execute("SELECT COUNT(*) FROM books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
    res = cur.fetchone()
    if res[0] == 0:
        return False
    cur.execute("SELECT STATUS, rowid FROM books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
    status, book_id = cur.fetchone()
    if status == "available":
        return "Book already available"
    cur.execute("UPDATE books SET STATUS = 'available', BORROWER = ?, DUE_DATE = NULL WHERE rowid = ?", ("None", book_id))
    cur.execute("DELETE FROM checked_out WHERE UserID = ?", (username,))
    con.commit()
    return True

def request_book(title, author):
    cur.execute("SELECT COUNT(*) FROM requested_books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
    res = cur.fetchone()
    if res[0] == 1:
        return False

    cur.execute("INSERT INTO requested_books (TITLE, AUTHOR) VALUES (?, ?)", (title, author))
    con.commit()
    return True
def find_request_books():
    cur.execute("SELECT * FROM requested_books")
    res = cur.fetchall()
    return res
def delete_request(title, author):
    cur.execute("SELECT COUNT(*) FROM requested_books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
    res = cur.fetchone()
    return res
    if res[0] != 1:
        return False
    cur.execute("SELECT rowid FROM requested_books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
    res = cur.fetchone()
    resfi = res[0]
    cur.execute(f"DELETE FROM requested_books WHERE rowid = {resfi}")
    con.commit()
    return True
@app.route("/")
def index():
    error = request.args.get("error")
    message = request.args.get("message")
    if error:
        error1 = error
    else:
        error1=""
    if session.get("username", False):
        username = session.get("username")
        pin = session.get("pin")
        return render_template("home.html", name=username, pin=pin, message=message)

        return    
    return render_template("login.html", error=error1, name="guest")

@app.route("/login", methods=['POST'])
def login():
    name = request.form.get("name", "User")
    pin = request.form.get("pin", "User")
    auth = auth_user(name, pin)
    if auth == "Incorrect pin":
        return redirect("/?error=Incorrect+pin!")
    elif auth == "No Account":
        return render_template("signup.html")
    else:
        session["username"] = name
        session["pin"] = pin
        return render_template("home.html", name=name, pin=pin)

@app.route("/signup", methods=['POST'])
def signup():
    name = request.form.get("name", "User")
    pin = request.form.get("pin", "User")
    if name == "":
        return redirect("/?error=Error!")
    if pin == "":
        return redirect("/?error=Error!")
    cur.execute("SELECT COUNT(*) FROM users WHERE USERNAME=?", (name, ))
    res = cur.fetchone()
    result = res[0]
    if result != 0:
        return redirect("/?error=Account+already+exists!+Signin+below:")
    
    cur.execute("INSERT INTO users (USERNAME, PIN) VALUES (?, ?)", (name, pin))
    con.commit()
    return redirect("/?error=User+has+been+added+to+the+system.+Login+below!")

@app.route("/action", methods=['GET', 'POST'])
def action():
    action = request.args.get("action")
    if action == "0":
        session.clear()
        return redirect("/")
    if action == "3":
        book_id = request.args.get("book_id", "0")

    if action == "1":
        cur.execute("SELECT SERIES FROM books")
        res = cur.fetchall()
        book_series = []
        for series in res:
            if series[0] not in book_series:
                if series[0] != None:
                    book_series.append(series[0])
        return render_template("add_book.html", book_series=book_series)
    if action == "2":
        return render_template("delete_book.html")
    if action == "11":
            title = request.args.get("title", "0")
            author = request.args.get("author", "0")
            ebook = request.args.get("ebook", "0")
            ebook_link = request.args.get("ebook_link", "None")
            status = "available"
            series = request.args.get("series", "None")
            series_num = request.args.get("series_num", "None")
            hehe = add_book(title, author, ebook, ebook_link, status, series, series_num)
            if hehe == True:
                return redirect("/?message=Book+Created")
            else:
                return redirect("/?message=Book+already+exists")
    if action == "12":
        title = request.args.get("title", "0")
        author = request.args.get("author", "0")
        hehe = delete_book(title, author)
        if hehe:
            return redirect("/?message=Book+Deleted")
        else:
            return redirect("/?message=Book+does+not+exist")
    if action == "3":
        book_id = request.args.get("book_id")
        res = checkout_book(book_id)
        if not res:
            return redirect("/?message=Unable+to+checkout+book!")
        return redirect("/?message=Sucessfully+checked+out+book!")
    if action == "4":
        title = request.args.get("book_title", "0")
        author = request.args.get("book_author", "0")
        res = return_book(title, author)
        if res:
            return redirect("/?message=Book+returned+sucessfully!")
        return redirect("/?message=Unable+to+return+book!")

    if action == "10":
        username = session.get("username", "notthere")
        title = request.args.get("book_title", "0")
        author = request.args.get("book_author", "0")
        results= find_book(title, author)
        book_id = results[0]
        status = results[1]
        borrower = results[2]
        ebook = results[3]
        ebook_link = results[4]
        series = results[5]
        series_num = results[6]
        due_date = results[7]
        return render_template("book_info.html", book_id=book_id, title=title, author=author, status=status, borrower=borrower, ebook=ebook, ebook_link=ebook_link, username=username, series=series, series_num=series_num, due_date=due_date)
    if action == "13":
        username = session.get("username", False)
        if not username:
            return render_template("error.html")
        cur.execute("SELECT COUNT(*) FROM books WHERE BORROWER = ?", (username, ))
        res = cur.fetchone()
        if res[0] == 0:
            message = "No Books Checked Out!"
        else:
            message = ""    
        cur.execute("SELECT * FROM books WHERE BORROWER = ?", (username, ))
        books = cur.fetchall()
        return render_template("checked_out_books.html", username=username, books=books, message=message)
    if action == "14":
        return redirect("/search?search=+")
    if action == "15":
        return render_template("request.html")
    if action == "16":
        title = request.args.get("title")
        author = request.args.get("author")
        hehe = request_book(title, author)
        if hehe:
                return redirect("/?message=Book+Requested")
        else:
                return redirect("/?message=Book+already+exists")
    
    if action == "17":
        books = find_request_books()
        return render_template("requested_books.html", books=books)
    if action == "18":
        title = request.args.get("title", "0")
        author = request.args.get("author", "0")
        cur.execute("SELECT COUNT(*) FROM requested_books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
        res = cur.fetchone()
        cur.execute("SELECT rowid FROM requested_books WHERE TITLE = ? AND AUTHOR = ?", (title, author))
        res = cur.fetchone()
        resfi = res[0]
        cur.execute(f"DELETE FROM requested_books WHERE rowid = {resfi}")
        con.commit()
        return redirect("/action?action=17")
        return True
    if action == "20":
        command = request.args.get("command", "SELECT * FROM books")
        args = request.args.get("args", "")
        cur.execute(f"{command}")
        con.commit()
        res = cur.fetchall()
        return render_template("error.html", error=res)
    else:
        return render_template("error.html")
@app.route("/search")
def search():
    search_term = request.args.get("search", False)
    if not search_term:
        return render_template("error.html")
    search = "%" + search_term + "%"
    cur.execute("SELECT * FROM books WHERE TITLE LIKE ?", (search, ))
    books = cur.fetchall()
    return render_template("search.html", search_term=search_term, books=books)
@app.route("/due")
def due():
    error = request.args.get("error")
    message = request.args.get("message")
    if error:
        error1 = error
    else:
        error1 = ""
    if session.get("username", False):
        username = session.get("username")
        pin = session.get("pin")
        
        today = datetime.datetime.now().date()
        soon_due = today + datetime.timedelta(days=2)

        cur.execute("SELECT title, due_date FROM books WHERE due_date = ? AND BORROWER=?", (today,username))
        due_today = cur.fetchall()

        cur.execute("SELECT title, due_date FROM books WHERE BORROWER=? AND due_date BETWEEN ? AND ?", (username, today, soon_due))
        due_soon = cur.fetchall()

        cur.execute("SELECT title, due_date FROM books WHERE due_date < ? AND BORROWER=?", (today, username))
        overdue = cur.fetchall()

        return render_template("due_books.html", name=username, due_today=due_today, due_soon=due_soon, overdue=overdue)

    return render_template("login.html", error=error1)
