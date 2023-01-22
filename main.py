from flask import (
    Flask, 
    request, 
    jsonify,
    )
from flask_login import LoginManager, login_user, current_user
from flask_apscheduler import APScheduler
from werkzeug.security import check_password_hash
from userlogin import UserLogin
from services import Connecting
import os


app = Flask(__name__)
app.secret_key = os.urandom(50)
conn: Connecting = Connecting()
login_manager = LoginManager(app)
scheduler = APScheduler()

conn.connect_db()
conn.create_tables()
conn.create_superuser('genitalgrinder90@gmail.com' ,'Brick92', 'root')
scheduler.init_app(app)
scheduler.start()


@login_manager.user_loader
def load_user(id):
    print('load_user')
    return UserLogin().fromDB(id)

@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        form = request.get_json()
        login = form['login']
        password = form['password']
        data = conn.check_user(login)
        if not data:
            return jsonify({
                "message" : "Данный логин не зарегистрирован"
            })
        elif login == data[0][2] and \
            check_password_hash(data[0][3], password) == False:
            return jsonify({
                "message" : "неправильный пароль"
            })
        elif login == data[0][2] and \
            check_password_hash(data[0][3], password) == True:
            userlogin = UserLogin().create(data[0])
            login_user(userlogin)
            user_id = current_user.get_id()
            token = conn.generate_token()
            conn.autorization(user_id, token)
            is_admin = conn.check_admin(login)
            scheduler.add_job(
                id = 'Scheduled Task', 
                func=conn.clear_token, 
                trigger="interval", 
                hours=24, 
                args=(user_id,)
            )
            if is_admin:
                return jsonify({
                    "user_id" : user_id,
                    "token" : token,
                    "редирект" : "на админку"
                })
            return jsonify({
                "user_id" : user_id,
                "token" : token,
                "редирект" : "на магазин"
            })
    return jsonify({
        "message" : "autorization"
    })

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        form = request.get_json()
        email = form['email']
        login = form['login']
        password = form['password']
        data = conn.check_user(login)
        mail_data = conn.check_user_mail(email)
        if data:
            return jsonify({
                "message" : "логин занят"
            })
        elif mail_data:
            return jsonify({
                "message" : "Данный адрес уже зарегистрирован"
            })
        elif not data and not mail_data and password:
            conn.registration(email, login, password)
            return jsonify({
                "редирект" : "на авторизацию"
            })
    return jsonify({
        "message" : "registration"
    })

@app.route('/shop')
def search():
    form = request.get_json()
    token = form['token']
    check = conn.check_token(token)
    if not check:
        return jsonify({
            "редирект" : "на авторизацию"
        })
    data = conn.get_games()
    return jsonify(data)

@app.route('/shop/<int:game_id>', methods=['GET', 'POST'])
def get_game(game_id):
    form = request.get_json()
    token = form['token']
    check = conn.check_token(token)
    if not check:
        return jsonify({
            "редирект" : "на авторизацию"
        })
    data = conn.list_result()
    basket_data = conn.check_add_in_basket(game_id)
    result: list[tuple] = []
    for i in data:
        if i[0] == int(game_id):
            price = i[5]
            result.append(i)
    if request.method == 'POST':
        form = request.get_json()
        user_id = form['user_id']
        data = conn.check_buy(game_id)
        if not data:
            return jsonify({
                "message" : "извините ключей не осталось"
            })
        elif data:
            if not basket_data:
                conn.add_to_basket(user_id, game_id)
                return jsonify({
                    "message" : "добавлено в корзину"
                }, result)
            else:
                return jsonify({
                    "message" : "товар уже добавлен"
                }, result)
    return jsonify(result)

@app.route('/shop/basket', methods=['GET', 'POST'])
def basket():
    form = request.get_json()
    token = form['token']
    check = conn.check_token(token)
    if not check:
        return jsonify({
            "редирект" : "на авторизацию"
        })
    summ = 0
    data = conn.check_basket()
    if request.method == 'POST':
        form = request.get_json()
        user_id = form['user_id']
        games = form['id_game']
        for i in games:
            price: float = conn.get_price(i)
            summ += price[0]
        print(summ)
        user_money = conn.check_money(user_id)
        if user_money[0] < summ:
            return jsonify({
                "message" : "У вас недостаточно средств"
            }, data)
        for j in games:
            key = conn.get_key(j)
            conn.key_send(key[0])
            conn.add_game_to_user(user_id, j, key[1])
        conn.buy(summ, user_id)
        return jsonify({
                "message" : "Поздравляем с приобретением!"
            }, data)
    return jsonify({
        "message" : "basket"
    }, data)

@app.route('/personal-cab/<int:id>', methods=['GET','POST'])
def personal_cab(id):
    form = request.get_json()
    token = form['token']
    check = conn.check_token(token)
    if not check:
        return jsonify({
            "редирект" : "на авторизацию"
        })
    personal_data = conn.get_user(id)
    games_data = conn.get_user_games(id)
    if request.method == 'POST':
        form = request.get_json()
        user_id = form['user_id']
        money = form['money']
        add_friend = form['add_friend']
        try:
            if int(money) > 0:
                conn.art_money(user_id, money)
                return jsonify({
                    "message" : "success"
                }, personal_data, 
                games_data, 
                user_id,
                )
        except:
            search = conn.search_friend(add_friend)
            if search:
                message = 'Найден пользователь'
                return jsonify(
                    personal_data, 
                    games_data, 
                    message, 
                    search,
                    )
            message = 'Пользователь не найден'
            return jsonify(
                personal_data, 
                games_data, 
                message,
                )
    return jsonify(personal_data, games_data)

@app.route('/admin')
def admin():
    form = request.get_json()
    token = form['token']
    check = conn.check_token(token)
    if not check:
        return jsonify({
            "редирект" : "на авторизацию"
        })
    return jsonify({
        "message" : "тут надо отловить 2 флеша и сделать ссылки на\
         добавления, жанров, игр и кодов"
    })

@app.route('/admin/ok/set-genres', methods=['GET', 'POST'])
def add_genre():
    form = request.get_json()
    token = form['token']
    check = conn.check_token(token)
    if not check:
        return jsonify({
            "редирект" : "на авторизацию"
        })
    data = conn.get_genres()
    if request.method == 'POST':
        form = request.get_json()
        title = form['title']
        if title:
            conn.set_genres(title)
            return jsonify({
                "message" : "Genre was added"
            }, data)
        return jsonify({
            "message" : "Fields must be not empty"
        }, data)
    return jsonify(data)

@app.route('/admin/ok/add-key', methods=['GET', 'POST'])
def add_key():
    form = request.get_json()
    token = form['token']
    check = conn.check_token(token)
    if not check:
        return jsonify({
            "редирект" : "на авторизацию"
        })
    result = conn.list_result()
    data = conn.get_games()
    if request.method == 'POST':
        form = request.get_json()
        key = form['key']
        game = form['game']
        code_data = conn.check_key(key)
        if len(key) != 25:
            return jsonify({
                "message" : "Длина ключа должна быть 25 символов"
            }, result,
            data,
            )
        elif not game:
            return jsonify({
                "message" : "Игра не выбрана"
            }, result, 
            data, 
            )
        elif code_data:
            return jsonify({
                "message" : "Ключ уже добавлен"
            }, result, 
            data, 
            )
        elif len(key) == 25 and data:
            conn.add_key(game, key)
            return jsonify({
                "message" : "Ключ добавлен"
            }, result, 
            data, 
            )
    return jsonify(result, data)

@app.route('/admin/add-game', methods=['GET', 'POST'])
def add_game():
    form = request.get_json()
    token = form['token']
    check = conn.check_token(token)
    if not check:
        return jsonify({
            "редирект" : "на авторизацию"
        })
    genre_data = conn.get_genres()
    games_data = conn.get_games()
    result = conn.list_result()
    if request.method == 'POST':
        form = request.get_json()
        title = form['title']
        description = form['description']
        price = form['price']
        year = form['year']
        genres = form['genre']
        if title and description \
            and genres and title not in games_data:
            conn.set_game(title, description, year, price)
            game = conn.get_game_id(title)
            game_id = game[0][0]
            for i in genres:
                conn.res(game_id, i)
            return jsonify({
                "message" : "Game added!"
            }, genre_data, 
            result, 
            )
        elif not title or not description \
            or not genres or title in games_data:
            return jsonify({
                "message" : "fields must not be empty"
            }, genre_data, 
            result, 
            )
    return jsonify(genre_data, result)


if __name__ == '__main__':
    app.run(port=1234, debug=True)