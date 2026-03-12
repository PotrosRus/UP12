import mysql.connector
from mysql.connector import Error
import tkinter as tk
from tkinter import ttk, messagebox, font
from tkinter import PhotoImage
from PIL import Image, ImageTk
import os
from datetime import datetime, timedelta
import decimal
import random


class Database:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                database='electron_shop',
                user='demoex',  # замените на вашего пользователя
                password='1234',  # замените на ваш пароль
                use_pure=True
            )
        except Error as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось подключиться к БД: {e}")

    def get_user(self, login, password):
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT u.*, r.name as role_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.id 
        WHERE u.login = %s AND u.password = %s
        """
        cursor.execute(query, (login, password))
        return cursor.fetchone()

    def get_all_products(self):
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM product_view ORDER BY name"
        cursor.execute(query)
        return cursor.fetchall()

    def get_filtered_products(self, search_text="", category="", manufacturer="", sort_by="name"):
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM product_view WHERE 1=1"
        params = []

        if search_text:
            query += " AND (name LIKE %s OR article LIKE %s)"
            params.append(f"%{search_text}%")
            params.append(f"%{search_text}%")

        if category and category != "Все категории":
            query += " AND category = %s"
            params.append(category)

        if manufacturer and manufacturer != "Все производители":
            query += " AND manufacturer = %s"
            params.append(manufacturer)

        # Сортировка
        if sort_by == "name":
            query += " ORDER BY name"
        elif sort_by == "price_asc":
            query += " ORDER BY price ASC"
        elif sort_by == "price_desc":
            query += " ORDER BY price DESC"
        elif sort_by == "discount":
            query += " ORDER BY discount DESC"

        cursor.execute(query, params)
        return cursor.fetchall()

    def get_categories(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        return cursor.fetchall()

    def get_manufacturers(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, name FROM manufacturers ORDER BY name")
        return cursor.fetchall()

    def get_suppliers(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id, name FROM suppliers ORDER BY name")
        return cursor.fetchall()

    def get_pickup_points(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pickup_points ORDER BY address")
        return cursor.fetchall()

    def get_pickup_point_by_address(self, address):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM pickup_points WHERE address = %s", (address,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_product_by_id(self, product_id):
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT p.*, c.name as category, m.name as manufacturer, s.name as supplier FROM products p LEFT JOIN categories c ON p.category_id = c.id LEFT JOIN manufacturers m ON p.manufacturer_id = m.id LEFT JOIN suppliers s ON p.supplier_id = s.id WHERE p.id = %s"
        cursor.execute(query, (product_id,))
        return cursor.fetchone()

    def get_product_by_article(self, article):
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM product_view WHERE article = %s"
        cursor.execute(query, (article,))
        return cursor.fetchone()

    def get_product_id_by_article(self, article):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM products WHERE article = %s", (article,))
        result = cursor.fetchone()
        return result[0] if result else None

    def add_product(self, product_data):
        cursor = self.connection.cursor()
        query = """
        INSERT INTO products (article, name, category_id, manufacturer_id, supplier_id, 
                             price, discount, quantity, description, photo, warranty_months)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, product_data)
        self.connection.commit()
        return cursor.lastrowid

    def update_product(self, product_id, product_data):
        cursor = self.connection.cursor()
        query = """
        UPDATE products 
        SET article=%s, name=%s, category_id=%s, manufacturer_id=%s, supplier_id=%s,
            price=%s, discount=%s, quantity=%s, description=%s, photo=%s, warranty_months=%s
        WHERE id=%s
        """
        cursor.execute(query, product_data + (product_id,))
        self.connection.commit()

    def delete_product(self, product_id):
        # Проверяем, есть ли заказы с этим товаром
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM order_items WHERE product_id = %s", (product_id,))
        count = cursor.fetchone()[0]

        if count > 0:
            raise Exception("Невозможно удалить товар, так как он есть в заказах")

        cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))
        self.connection.commit()

    def get_orders(self, filters=None):
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT o.*, u.full_name, p.address 
        FROM orders o
        JOIN users u ON o.user_id = u.id
        JOIN pickup_points p ON o.pickup_point_id = p.id
        WHERE 1=1
        """
        params = []

        if filters:
            if filters.get('status') and filters['status'] != "Все статусы":
                query += " AND o.status = %s"
                params.append(filters['status'])

            if filters.get('search'):
                query += " AND (o.order_number LIKE %s OR u.full_name LIKE %s)"
                params.append(f"%{filters['search']}%")
                params.append(f"%{filters['search']}%")

            if filters.get('user_id'):
                query += " AND o.user_id = %s"
                params.append(filters['user_id'])

            if filters.get('date_from'):
                query += " AND o.order_date >= %s"
                params.append(filters['date_from'])

            if filters.get('date_to'):
                query += " AND o.order_date <= %s"
                params.append(filters['date_to'])

        query += " ORDER BY o.order_date DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

    def get_order_details(self, order_id):
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT oi.*, p.name, p.article, p.price, p.discount
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
        """
        cursor.execute(query, (order_id,))
        return cursor.fetchall()

    def create_order(self, order_data, items_data):
        cursor = self.connection.cursor()
        try:
            # Начинаем транзакцию
            cursor.execute("START TRANSACTION")

            # Вставляем заказ
            order_query = """
            INSERT INTO orders (order_number, order_date, delivery_date, pickup_point_id, 
                              user_id, pickup_code, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(order_query, order_data)
            order_id = cursor.lastrowid

            # Вставляем позиции заказа
            item_query = """
            INSERT INTO order_items (order_id, product_id, quantity, price_at_order)
            VALUES (%s, %s, %s, %s)
            """

            for item in items_data:
                # Проверяем наличие товара
                cursor.execute("SELECT quantity FROM products WHERE id = %s", (item['product_id'],))
                current_qty = cursor.fetchone()[0]
                if current_qty < item['quantity']:
                    raise Exception(f"Недостаточно товара на складе. Доступно: {current_qty}")

                cursor.execute(item_query, (order_id, item['product_id'],
                                            item['quantity'], item['price']))

                # Обновляем количество товара на складе
                update_query = "UPDATE products SET quantity = quantity - %s WHERE id = %s"
                cursor.execute(update_query, (item['quantity'], item['product_id']))

            # Подтверждаем транзакцию
            self.connection.commit()
            return order_id

        except Exception as e:
            # Откатываем транзакцию в случае ошибки
            self.connection.rollback()
            raise e

    def update_order(self, order_id, order_data, items_data):
        cursor = self.connection.cursor()
        try:
            cursor.execute("START TRANSACTION")

            # Получаем старые позиции для возврата товаров
            cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = %s", (order_id,))
            old_items = cursor.fetchall()

            # Возвращаем старые товары на склад
            for product_id, quantity in old_items:
                cursor.execute("UPDATE products SET quantity = quantity + %s WHERE id = %s",
                               (quantity, product_id))

            # Удаляем старые позиции
            cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))

            # Обновляем заказ
            update_query = """
            UPDATE orders 
            SET delivery_date=%s, pickup_point_id=%s, status=%s
            WHERE id=%s
            """
            cursor.execute(update_query, (order_data['delivery_date'],
                                          order_data['pickup_point_id'],
                                          order_data['status'], order_id))

            # Добавляем новые позиции
            item_query = """
            INSERT INTO order_items (order_id, product_id, quantity, price_at_order)
            VALUES (%s, %s, %s, %s)
            """

            for item in items_data:
                # Проверяем наличие
                cursor.execute("SELECT quantity FROM products WHERE id = %s", (item['product_id'],))
                current_qty = cursor.fetchone()[0]
                if current_qty < item['quantity']:
                    raise Exception(f"Недостаточно товара на складе. Доступно: {current_qty}")

                cursor.execute(item_query, (order_id, item['product_id'],
                                            item['quantity'], item['price']))

                # Обновляем количество
                cursor.execute("UPDATE products SET quantity = quantity - %s WHERE id = %s",
                               (item['quantity'], item['product_id']))

            self.connection.commit()

        except Exception as e:
            self.connection.rollback()
            raise e

    def update_order_status(self, order_id, new_status):
        cursor = self.connection.cursor()

        # Получаем старый статус для логирования
        cursor.execute("SELECT order_number, status FROM orders WHERE id = %s", (order_id,))
        old_data = cursor.fetchone()

        query = "UPDATE orders SET status = %s WHERE id = %s"
        cursor.execute(query, (new_status, order_id))
        self.connection.commit()

        return old_data  # Возвращаем старые данные для логирования

    def delete_order(self, order_id):
        cursor = self.connection.cursor()
        try:
            # Получаем позиции заказа для возврата товаров
            cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = %s", (order_id,))
            items = cursor.fetchall()

            # Возвращаем товары на склад
            for product_id, quantity in items:
                cursor.execute("UPDATE products SET quantity = quantity + %s WHERE id = %s",
                               (quantity, product_id))

            # Удаляем позиции заказа
            cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))

            # Удаляем заказ
            cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))

            self.connection.commit()

        except Exception as e:
            self.connection.rollback()
            raise e

    def get_category_id(self, category_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM categories WHERE name = %s", (category_name,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_category_name(self, category_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM categories WHERE id = %s", (category_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_manufacturer_id(self, manufacturer_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM manufacturers WHERE name = %s", (manufacturer_name,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_manufacturer_name(self, manufacturer_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM manufacturers WHERE id = %s", (manufacturer_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_supplier_id(self, supplier_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT id FROM suppliers WHERE name = %s", (supplier_name,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_supplier_name(self, supplier_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM suppliers WHERE id = %s", (supplier_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def generate_order_number(self):
        """Генерирует уникальный номер заказа"""
        prefix = "ORD"
        date_part = datetime.now().strftime("%Y%m%d")
        random_part = str(random.randint(1000, 9999))
        return f"{prefix}{date_part}{random_part}"

    def generate_pickup_code(self):
        """Генерирует код получения заказа"""
        return str(random.randint(1000, 9999))

    def log_action(self, user_id, user_name, action_type, entity_type, entity_id=None,
                   entity_details=None, old_values=None, new_values=None):
        """Запись действия в лог"""
        cursor = self.connection.cursor()
        query = """
        INSERT INTO action_logs 
        (user_id, user_name, action_type, entity_type, entity_id, entity_details, 
         old_values, new_values, action_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Преобразуем словари в JSON
        import json
        old_json = json.dumps(old_values, ensure_ascii=False) if old_values else None
        new_json = json.dumps(new_values, ensure_ascii=False) if new_values else None

        cursor.execute(query, (
            user_id, user_name, action_type, entity_type, entity_id, entity_details,
            old_json, new_json, datetime.now()
        ))
        self.connection.commit()

    def get_action_logs(self, filters=None):
        """Получение логов с фильтрацией"""
        cursor = self.connection.cursor(dictionary=True)
        query = """
        SELECT * FROM action_logs 
        WHERE 1=1
        """
        params = []

        if filters:
            if filters.get('user_id'):
                query += " AND user_id = %s"
                params.append(filters['user_id'])

            if filters.get('action_type') and filters['action_type'] != "Все действия":
                query += " AND action_type = %s"
                params.append(filters['action_type'])

            if filters.get('entity_type') and filters['entity_type'] != "Все сущности":
                query += " AND entity_type = %s"
                params.append(filters['entity_type'])

            if filters.get('date_from'):
                query += " AND DATE(action_date) >= %s"
                params.append(filters['date_from'])

            if filters.get('date_to'):
                query += " AND DATE(action_date) <= %s"
                params.append(filters['date_to'])

            if filters.get('search'):
                query += """ AND (
                    user_name LIKE %s OR 
                    entity_details LIKE %s OR 
                    CAST(entity_id AS CHAR) LIKE %s
                )"""
                search_term = f"%{filters['search']}%"
                params.extend([search_term, search_term, search_term])

        query += " ORDER BY action_date DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

class LoginWindow:
    def __init__(self, db):
        self.db = db
        self.window = tk.Tk()
        self.window.title("Электрон - Вход в систему")
        self.window.geometry("400x500")
        self.window.configure(bg='#FFFFFF')

        # Центрируем окно
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

        # Попытка установить иконку
        try:
            self.window.iconbitmap(default="icon.ico")
        except:
            pass

        # Шрифт
        self.default_font = font.Font(family="Times New Roman", size=12)
        self.window.option_add("*Font", self.default_font)

        self.setup_ui()

    def setup_ui(self):
        # Логотип
        try:
            if os.path.exists("logo.png"):
                logo_img = Image.open("logo.png")
                logo_img = logo_img.resize((200, 100), Image.Resampling.LANCZOS)
                self.logo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(self.window, image=self.logo, bg='#FFFFFF')
                logo_label.pack(pady=20)
            else:
                raise FileNotFoundError
        except:
            title_label = tk.Label(self.window, text="ЭЛЕКТРОН",
                                   font=("Times New Roman", 24, "bold"),
                                   bg='#FFFFFF', fg='#7FFF00')
            title_label.pack(pady=30)

        # Форма входа
        frame = tk.Frame(self.window, bg='#FFFFFF')
        frame.pack(expand=True)

        tk.Label(frame, text="Логин:", bg='#FFFFFF').grid(row=0, column=0, pady=10, sticky='e')
        self.login_entry = tk.Entry(frame, width=25, font=("Times New Roman", 12))
        self.login_entry.grid(row=0, column=1, pady=10, padx=10)

        tk.Label(frame, text="Пароль:", bg='#FFFFFF').grid(row=1, column=0, pady=10, sticky='e')
        self.password_entry = tk.Entry(frame, width=25, font=("Times New Roman", 12), show="*")
        self.password_entry.grid(row=1, column=1, pady=10, padx=10)

        # Кнопки
        btn_frame = tk.Frame(frame, bg='#FFFFFF')
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)

        login_btn = tk.Button(btn_frame, text="Войти", command=self.login,
                              bg='#00FA9A', fg='black', width=15, height=2,
                              font=("Times New Roman", 12, "bold"))
        login_btn.pack(side=tk.LEFT, padx=5)

        guest_btn = tk.Button(btn_frame, text="Войти как гость", command=self.guest_login,
                              bg='#7FFF00', fg='black', width=15, height=2,
                              font=("Times New Roman", 12))
        guest_btn.pack(side=tk.LEFT, padx=5)

        # Статус
        self.status_label = tk.Label(self.window, text="", bg='#FFFFFF', fg='red')
        self.status_label.pack(pady=10)

        # Привязка Enter
        self.password_entry.bind('<Return>', lambda e: self.login())

    def login(self):
        login = self.login_entry.get()
        password = self.password_entry.get()

        if not login or not password:
            self.status_label.config(text="Введите логин и пароль")
            return

        user = self.db.get_user(login, password)
        if user:
            self.window.destroy()
            MainApp(self.db, user)
        else:
            self.status_label.config(text="Неверный логин или пароль")

    def guest_login(self):
        self.window.destroy()
        guest_user = {'id': 0, 'full_name': 'Гость', 'role_name': 'Гость', 'role_id': 4}
        MainApp(self.db, guest_user)

    def run(self):
        self.window.mainloop()


class MainApp:
    def __init__(self, db, user):
        self.db = db
        self.user = user
        self.root = tk.Tk()
        self.root.title(f"Электрон - {user['full_name']}")
        self.root.geometry("1400x700")
        self.root.configure(bg='#FFFFFF')

        # Центрируем окно
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        # Шрифт
        self.default_font = font.Font(family="Times New Roman", size=10)
        self.root.option_add("*Font", self.default_font)

        self.setup_menu()
        self.setup_main_frame()

        # Показываем товары по умолчанию
        self.show_products()

    def setup_menu(self):
        # Верхняя панель
        top_frame = tk.Frame(self.root, bg='#7FFF00', height=50)
        top_frame.pack(fill=tk.X)
        top_frame.pack_propagate(False)

        # Логотип
        try:
            if os.path.exists("logo.png"):
                logo_img = Image.open("logo.png")
                logo_img = logo_img.resize((100, 40), Image.Resampling.LANCZOS)
                self.logo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(top_frame, image=self.logo, bg='#7FFF00')
                logo_label.pack(side=tk.LEFT, padx=10)
            else:
                raise FileNotFoundError
        except:
            tk.Label(top_frame, text="ЭЛЕКТРОН", font=("Times New Roman", 16, "bold"),
                     bg='#7FFF00').pack(side=tk.LEFT, padx=10)

        # Информация о пользователе
        user_frame = tk.Frame(top_frame, bg='#7FFF00')
        user_frame.pack(side=tk.RIGHT, padx=20)

        tk.Label(user_frame, text=f"Пользователь: {self.user['full_name']}",
                 font=("Times New Roman", 12, "bold"), bg='#7FFF00').pack(side=tk.LEFT, padx=10)

        logout_btn = tk.Button(user_frame, text="Выход", command=self.logout,
                               bg='#00FA9A', fg='black', width=8)
        logout_btn.pack(side=tk.LEFT)

        # Нижняя панель навигации
        nav_frame = tk.Frame(self.root, bg='#FFFFFF', height=40)
        nav_frame.pack(fill=tk.X, pady=5)

        buttons = [
            ("Товары", self.show_products),
        ]

        # Добавляем кнопки в зависимости от роли
        if self.user['role_name'] in ['Менеджер', 'Администратор', 'Авторизированный клиент']:
            buttons.append(("Мои заказы", self.show_my_orders))

        if self.user['role_name'] in ['Менеджер', 'Администратор']:
            buttons.append(("Все заказы", self.show_all_orders))

        if self.user['role_name'] == 'Администратор':
            buttons.extend([
                ("Добавить товар", self.add_product),
                ("Управление заказами", self.manage_orders)
            ])
        if self.user['role_name'] == 'Администратор':
            buttons.extend([
                ("Добавить товар", self.add_product),
                ("Управление заказами", self.manage_orders),
                ("📋 Журнал действий", self.show_logs)  # Добавьте эту строку
            ])
        for text, command in buttons:
            btn = tk.Button(nav_frame, text=text, command=command,
                            bg='#7FFF00', fg='black', width=15, height=1)
            btn.pack(side=tk.LEFT, padx=5)

    def setup_main_frame(self):
        self.main_frame = tk.Frame(self.root, bg='#FFFFFF')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def format_price(self, price):
        """Форматирование цены"""
        if isinstance(price, decimal.Decimal):
            return f"{float(price):,.0f} ₽".replace(',', ' ')
        return f"{price:,.0f} ₽".replace(',', ' ')

    def show_products(self):
        self.clear_main_frame()

        # Заголовок
        title = tk.Label(self.main_frame, text="Каталог товаров",
                         font=("Times New Roman", 18, "bold"), bg='#FFFFFF')
        title.pack(pady=10)

        # Панель фильтрации (только для менеджера и администратора)
        if self.user['role_name'] in ['Менеджер', 'Администратор']:
            filter_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
            filter_frame.pack(fill=tk.X, pady=10)

            # Поиск
            tk.Label(filter_frame, text="Поиск:", bg='#FFFFFF').grid(row=0, column=0, padx=5, sticky='e')
            self.search_entry = tk.Entry(filter_frame, width=30)
            self.search_entry.grid(row=0, column=1, padx=5)
            self.search_entry.bind('<KeyRelease>', lambda e: self.load_products())

            # Категории
            tk.Label(filter_frame, text="Категория:", bg='#FFFFFF').grid(row=0, column=2, padx=5, sticky='e')
            categories = ["Все категории"] + [cat[1] for cat in self.db.get_categories()]
            self.category_var = tk.StringVar(value="Все категории")
            self.category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var,
                                               values=categories, width=20, state='readonly')
            self.category_combo.grid(row=0, column=3, padx=5)
            self.category_combo.bind('<<ComboboxSelected>>', lambda e: self.load_products())

            # Производители
            tk.Label(filter_frame, text="Производитель:", bg='#FFFFFF').grid(row=0, column=4, padx=5, sticky='e')
            manufacturers = ["Все производители"] + [man[1] for man in self.db.get_manufacturers()]
            self.manufacturer_var = tk.StringVar(value="Все производители")
            self.manufacturer_combo = ttk.Combobox(filter_frame, textvariable=self.manufacturer_var,
                                                   values=manufacturers, width=20, state='readonly')
            self.manufacturer_combo.grid(row=0, column=5, padx=5)
            self.manufacturer_combo.bind('<<ComboboxSelected>>', lambda e: self.load_products())

            # Сортировка
            tk.Label(filter_frame, text="Сортировка:", bg='#FFFFFF').grid(row=0, column=6, padx=5, sticky='e')
            sort_options = [
                ("По названию", "name"),
                ("Цена (возр.)", "price_asc"),
                ("Цена (уб.)", "price_desc"),
                ("По скидке", "discount")
            ]
            self.sort_var = tk.StringVar(value="По названию")
            self.sort_combo = ttk.Combobox(filter_frame, textvariable=self.sort_var,
                                           values=[opt[0] for opt in sort_options], width=15, state='readonly')
            self.sort_combo.grid(row=0, column=7, padx=5)
            self.sort_combo.bind('<<ComboboxSelected>>', lambda e: self.load_products())

            # Сохраняем соответствие названий сортировки
            self.sort_mapping = {opt[0]: opt[1] for opt in sort_options}

        # Контейнер для товаров с прокруткой
        canvas_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, bg='#FFFFFF', highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg='#FFFFFF')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)

        # Обновляем ширину canvas при изменении размера
        def configure_canvas(event):
            canvas.itemconfig(1, width=event.width)

        canvas.bind('<Configure>', configure_canvas)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Загружаем товары
        self.load_products()

    def load_products(self):
        # Очищаем предыдущие товары
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Получаем товары с фильтрацией
        if self.user['role_name'] in ['Менеджер', 'Администратор']:
            search_text = self.search_entry.get() if hasattr(self, 'search_entry') else ""
            category = self.category_var.get() if hasattr(self, 'category_var') else "Все категории"
            manufacturer = self.manufacturer_var.get() if hasattr(self, 'manufacturer_var') else "Все производители"
            sort_display = self.sort_var.get() if hasattr(self, 'sort_var') else "По названию"
            sort_by = self.sort_mapping.get(sort_display, "name") if hasattr(self, 'sort_mapping') else "name"

            products = self.db.get_filtered_products(search_text, category, manufacturer, sort_by)
        else:
            products = self.db.get_all_products()

        if not products:
            no_products_label = tk.Label(self.scrollable_frame, text="Товары не найдены",
                                         font=("Times New Roman", 14), bg='#FFFFFF')
            no_products_label.pack(pady=50)
            return

        # Заголовки
        headers = ["Фото", "Наименование", "Категория", "Производитель",
                   "Поставщик", "Цена", "Скидка", "Кол-во", "Гарантия"]

        if self.user['role_name'] == 'Администратор':
            headers.append("Действия")
        elif self.user['role_name'] in ['Менеджер', 'Авторизированный клиент']:
            headers.append("Заказ")

        for col, header in enumerate(headers):
            label = tk.Label(self.scrollable_frame, text=header, font=("Times New Roman", 11, "bold"),
                             bg='#7FFF00', padx=5, pady=5, relief=tk.RIDGE)
            label.grid(row=0, column=col, sticky="ew", padx=1, pady=1)

        # Настраиваем веса колонок
        for col in range(len(headers)):
            self.scrollable_frame.grid_columnconfigure(col, weight=1)

        # Товары
        for row, product in enumerate(products, start=1):
            # Конвертируем Decimal в float для вычислений
            price = float(product['price']) if isinstance(product['price'], decimal.Decimal) else product['price']
            discount = float(product['discount']) if isinstance(product['discount'], decimal.Decimal) else product[
                'discount']
            quantity = int(product['quantity']) if product['quantity'] else 0

            # Определяем цвет фона
            bg_color = '#FFFFFF'
            if discount > 15:
                bg_color = '#2E8B57'
            elif quantity == 0:
                bg_color = '#E6F3FF'

            # Фото (заглушка)
            photo_frame = tk.Frame(self.scrollable_frame, bg=bg_color, width=80, height=80)
            photo_frame.grid(row=row, column=0, padx=1, pady=1, sticky="nsew")
            photo_frame.grid_propagate(False)

            try:
                # Пытаемся загрузить фото товара
                img_path = f"images/{product['photo']}"
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                else:
                    img = Image.open("picture.png")  # заглушка
                img = img.resize((70, 70), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                label = tk.Label(photo_frame, image=photo, bg=bg_color)
                label.image = photo
                label.pack(expand=True)
            except Exception as e:
                # Если нет изображения, показываем заглушку
                try:
                    if os.path.exists("picture.png"):
                        img = Image.open("picture.png")
                        img = img.resize((70, 70), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        label = tk.Label(photo_frame, image=photo, bg=bg_color)
                        label.image = photo
                        label.pack(expand=True)
                    else:
                        tk.Label(photo_frame, text="Нет фото", bg=bg_color, font=("Times New Roman", 8)).pack(
                            expand=True)
                except:
                    tk.Label(photo_frame, text="Нет фото", bg=bg_color, font=("Times New Roman", 8)).pack(expand=True)

            # Данные товара
            data = [
                product['name'],
                product['category'],
                product['manufacturer'],
                product['supplier'],
            ]

            # Цена со скидкой
            if discount > 0:
                price_text = self.format_price(price)
                final_price = price * (1 - discount / 100)
                price_display = f"{price_text}\n{self.format_price(final_price)}"
                price_color = 'red'
            else:
                price_display = self.format_price(price)
                price_color = 'black'

            # Создаем ячейки для основных данных
            for col, value in enumerate(data, start=1):
                label = tk.Label(self.scrollable_frame, text=value, bg=bg_color,
                                 padx=5, pady=5, relief=tk.RIDGE, wraplength=150)
                label.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

            # Цена
            price_label = tk.Label(self.scrollable_frame, text=price_display, bg=bg_color,
                                   fg=price_color, padx=5, pady=5, relief=tk.RIDGE,
                                   font=("Times New Roman", 10, "bold"))
            price_label.grid(row=row, column=5, sticky="nsew", padx=1, pady=1)

            # Скидка
            discount_text = f"{discount:.0f}%" if discount else "0%"
            discount_label = tk.Label(self.scrollable_frame, text=discount_text, bg=bg_color,
                                      padx=5, pady=5, relief=tk.RIDGE)
            discount_label.grid(row=row, column=6, sticky="nsew", padx=1, pady=1)

            # Количество
            quantity_label = tk.Label(self.scrollable_frame, text=quantity, bg=bg_color,
                                      padx=5, pady=5, relief=tk.RIDGE)
            quantity_label.grid(row=row, column=7, sticky="nsew", padx=1, pady=1)

            # Гарантия
            warranty_months = int(product['warranty_months']) if product['warranty_months'] else 0
            warranty_text = f"{warranty_months} мес."
            warranty_label = tk.Label(self.scrollable_frame, text=warranty_text, bg=bg_color,
                                      padx=5, pady=5, relief=tk.RIDGE)
            warranty_label.grid(row=row, column=8, sticky="nsew", padx=1, pady=1)

            # Кнопки действий для администратора
            if self.user['role_name'] == 'Администратор':
                btn_frame = tk.Frame(self.scrollable_frame, bg=bg_color)
                btn_frame.grid(row=row, column=9, padx=1, pady=1, sticky="nsew")

                edit_btn = tk.Button(btn_frame, text="✏️",
                                     command=lambda p=product: self.edit_product(p),
                                     bg='#00FA9A', width=3)
                edit_btn.pack(side=tk.LEFT, padx=2, pady=2)

                delete_btn = tk.Button(btn_frame, text="🗑️",
                                       command=lambda p=product: self.delete_product(p),
                                       bg='#FF6B6B', width=3)
                delete_btn.pack(side=tk.LEFT, padx=2, pady=2)

            # Кнопка "Заказать" для менеджеров и авторизованных клиентов
            elif self.user['role_name'] in ['Менеджер', 'Авторизированный клиент'] and quantity > 0:
                btn_frame = tk.Frame(self.scrollable_frame, bg=bg_color)
                btn_frame.grid(row=row, column=9, padx=1, pady=1, sticky="nsew")

                order_btn = tk.Button(btn_frame, text="Заказать",
                                      command=lambda p=product: self.quick_order(p),
                                      bg='#00FA9A', width=8)
                order_btn.pack(padx=2, pady=2)

    def quick_order(self, product):
        """Быстрое создание заказа на один товар"""
        # Создаем окно для оформления заказа
        order_window = tk.Toplevel(self.root)
        order_window.title(f"Оформление заказа - {product['name']}")
        order_window.geometry("500x600")
        order_window.configure(bg='#FFFFFF')

        # Центрируем окно
        order_window.update_idletasks()
        width = order_window.winfo_width()
        height = order_window.winfo_height()
        x = (order_window.winfo_screenwidth() // 2) - (width // 2)
        y = (order_window.winfo_screenheight() // 2) - (height // 2)
        order_window.geometry(f'{width}x{height}+{x}+{y}')

        # Заголовок
        tk.Label(order_window, text="Оформление заказа",
                 font=("Times New Roman", 16, "bold"), bg='#FFFFFF').pack(pady=10)

        # Информация о товаре
        product_frame = tk.Frame(order_window, bg='#F0F0F0', relief=tk.RAISED, bd=2)
        product_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(product_frame, text=f"Товар: {product['name']}",
                 bg='#F0F0F0', font=("Times New Roman", 12)).pack(anchor='w', padx=10, pady=5)

        price = float(product['price'])
        discount = float(product['discount'])
        final_price = price * (1 - discount / 100) if discount > 0 else price

        tk.Label(product_frame, text=f"Цена: {self.format_price(final_price)}",
                 bg='#F0F0F0', font=("Times New Roman", 12, "bold"), fg='#2E8B57').pack(anchor='w', padx=10, pady=5)

        tk.Label(product_frame, text=f"Доступно: {product['quantity']} шт.",
                 bg='#F0F0F0').pack(anchor='w', padx=10, pady=5)

        # Форма заказа
        form_frame = tk.Frame(order_window, bg='#FFFFFF')
        form_frame.pack(pady=20)

        # Количество
        tk.Label(form_frame, text="Количество:", bg='#FFFFFF').grid(row=0, column=0, pady=10, padx=5, sticky='e')
        quantity_var = tk.StringVar(value="1")
        quantity_spinbox = tk.Spinbox(form_frame, from_=1, to=product['quantity'],
                                      textvariable=quantity_var, width=10)
        quantity_spinbox.grid(row=0, column=1, pady=10, padx=5, sticky='w')

        # Пункт выдачи
        tk.Label(form_frame, text="Пункт выдачи:", bg='#FFFFFF').grid(row=1, column=0, pady=10, padx=5, sticky='e')
        pickup_points = self.db.get_pickup_points()
        pickup_addresses = [p['address'] for p in pickup_points]

        pickup_var = tk.StringVar()
        pickup_combo = ttk.Combobox(form_frame, textvariable=pickup_var,
                                    values=pickup_addresses, width=40, state='readonly')
        pickup_combo.grid(row=1, column=1, pady=10, padx=5)

        if pickup_addresses:
            pickup_combo.current(0)

        # Дата доставки
        tk.Label(form_frame, text="Дата доставки:", bg='#FFFFFF').grid(row=2, column=0, pady=10, padx=5, sticky='e')

        dates = []
        for i in range(1, 8):
            date = datetime.now() + timedelta(days=i)
            dates.append(date.strftime('%Y-%m-%d'))

        delivery_var = tk.StringVar()
        delivery_combo = ttk.Combobox(form_frame, textvariable=delivery_var,
                                      values=dates, width=20, state='readonly')
        delivery_combo.grid(row=2, column=1, pady=10, padx=5, sticky='w')
        delivery_combo.current(0)

        # Итоговая сумма
        total_frame = tk.Frame(order_window, bg='#F0F0F0', relief=tk.RAISED, bd=2)
        total_frame.pack(fill=tk.X, padx=20, pady=20)

        def update_total(*args):
            try:
                qty = int(quantity_var.get())
                total = final_price * qty
                total_label.config(text=f"ИТОГО: {self.format_price(total)}")
            except:
                pass

        quantity_var.trace('w', update_total)

        total_label = tk.Label(total_frame, text=f"ИТОГО: {self.format_price(final_price)}",
                               font=("Times New Roman", 14, "bold"), bg='#F0F0F0',
                               fg='#2E8B57')
        total_label.pack(pady=10)

        # Кнопки
        btn_frame = tk.Frame(order_window, bg='#FFFFFF')
        btn_frame.pack(pady=20)

        def confirm_order():
            try:
                quantity = int(quantity_var.get())
                if quantity <= 0 or quantity > product['quantity']:
                    messagebox.showerror("Ошибка", "Некорректное количество")
                    return

                if not pickup_var.get():
                    messagebox.showerror("Ошибка", "Выберите пункт выдачи")
                    return

                if not delivery_var.get():
                    messagebox.showerror("Ошибка", "Выберите дату доставки")
                    return

                # Подготовка данных заказа
                order_number = self.db.generate_order_number()
                order_date = datetime.now().date()
                delivery_date = datetime.strptime(delivery_var.get(), '%Y-%m-%d').date()
                pickup_point_id = self.db.get_pickup_point_by_address(pickup_var.get())
                user_id = self.user['id'] if self.user['id'] != 0 else 1
                pickup_code = self.db.generate_pickup_code()
                status = "Новый"

                order_data = (order_number, order_date, delivery_date, pickup_point_id,
                              user_id, pickup_code, status)

                # Получаем ID товара
                product_id = self.db.get_product_id_by_article(product['article'])

                # Подготовка позиций заказа
                items_data = [{
                    'product_id': product_id,
                    'quantity': quantity,
                    'price': final_price
                }]

                # Создаем заказ
                order_id = self.db.create_order(order_data, items_data)

                # Логирование создания заказа
                total = final_price * quantity
                self.db.log_action(
                    user_id=self.user['id'],
                    user_name=self.user['full_name'],
                    action_type='CREATE',
                    entity_type='ORDER',
                    entity_id=order_id,
                    entity_details=f"Создан заказ №{order_number} на сумму {self.format_price(total)}",
                    new_values={
                        'order_number': order_number,
                        'order_date': str(order_date),
                        'delivery_date': str(delivery_date),
                        'pickup_point_id': pickup_point_id,
                        'user_id': user_id,
                        'status': status,
                        'items_count': 1,
                        'total': total
                    }
                )

                messagebox.showinfo("Успех",
                                    f"Заказ №{order_number} успешно создан!\n"
                                    f"Код получения: {pickup_code}\n"
                                    f"Дата доставки: {delivery_date}")

                order_window.destroy()
                self.show_my_orders()

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать заказ: {e}")

        tk.Button(btn_frame, text="Подтвердить заказ", command=confirm_order,
                  bg='#00FA9A', width=20, height=2, font=("Times New Roman", 11, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(btn_frame, text="Отмена", command=order_window.destroy,
                  bg='#FF6B6B', width=15, height=2).pack(side=tk.LEFT, padx=10)

    def edit_product(self, product):
        """Редактирование товара"""
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Редактирование товара - {product['name']}")
        edit_window.geometry("600x700")
        edit_window.configure(bg='#FFFFFF')

        # Центрируем окно
        edit_window.update_idletasks()
        width = edit_window.winfo_width()
        height = edit_window.winfo_height()
        x = (edit_window.winfo_screenwidth() // 2) - (width // 2)
        y = (edit_window.winfo_screenheight() // 2) - (height // 2)
        edit_window.geometry(f'{width}x{height}+{x}+{y}')

        # Заголовок
        tk.Label(edit_window, text="Редактирование товара",
                 font=("Times New Roman", 16, "bold"), bg='#FFFFFF').pack(pady=10)

        # Форма редактирования
        form_frame = tk.Frame(edit_window, bg='#FFFFFF')
        form_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # Создаем Canvas с прокруткой для формы
        canvas = tk.Canvas(form_frame, bg='#FFFFFF', highlightthickness=0)
        scrollbar = tk.Scrollbar(form_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#FFFFFF')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Поля для редактирования
        fields = [
            ("Артикул:", product['article']),
            ("Наименование:", product['name']),
            ("Категория:", "combo", [cat[1] for cat in self.db.get_categories()], product['category']),
            ("Производитель:", "combo", [man[1] for man in self.db.get_manufacturers()], product['manufacturer']),
            ("Поставщик:", "combo", [sup[1] for sup in self.db.get_suppliers()], product['supplier']),
            ("Цена:", str(product['price'])),
            ("Скидка %:", str(product['discount'])),
            ("Количество:", str(product['quantity'])),
            ("Гарантия (мес):", str(product['warranty_months'])),
            ("Описание:", "text", product['description'] if product['description'] else "")
        ]

        self.edit_entries = {}

        for i, field_info in enumerate(fields):
            if len(field_info) == 2:
                label_text, value = field_info
                field_type = "entry"
                values = None
            elif len(field_info) == 4:
                label_text, field_type, values, value = field_info
            else:
                continue

            tk.Label(scrollable_frame, text=label_text, bg='#FFFFFF', font=("Times New Roman", 11)).grid(
                row=i, column=0, pady=5, padx=5, sticky='e')

            if field_type == "entry":
                entry = tk.Entry(scrollable_frame, width=40, font=("Times New Roman", 11))
                entry.insert(0, value)
                entry.grid(row=i, column=1, pady=5, padx=5)
                self.edit_entries[label_text] = entry
            elif field_type == "combo":
                var = tk.StringVar(value=value)
                combo = ttk.Combobox(scrollable_frame, textvariable=var, values=values,
                                     width=38, font=("Times New Roman", 11), state='readonly')
                combo.grid(row=i, column=1, pady=5, padx=5)
                self.edit_entries[label_text] = var
            elif field_type == "text":
                text_frame = tk.Frame(scrollable_frame)
                text_frame.grid(row=i, column=1, pady=5, padx=5, sticky='w')
                text = tk.Text(text_frame, width=40, height=5, font=("Times New Roman", 11))
                text.insert("1.0", value)
                text.pack(side=tk.LEFT)
                scrollbar_text = tk.Scrollbar(text_frame, command=text.yview)
                scrollbar_text.pack(side=tk.RIGHT, fill=tk.Y)
                text.config(yscrollcommand=scrollbar_text.set)
                self.edit_entries[label_text] = text

        # Кнопки
        btn_frame = tk.Frame(edit_window, bg='#FFFFFF')
        btn_frame.pack(pady=20)

        def save_changes():
            try:
                # Сбор данных из формы
                article = self.edit_entries["Артикул:"].get().strip()
                name = self.edit_entries["Наименование:"].get().strip()
                category = self.edit_entries["Категория:"].get()
                manufacturer = self.edit_entries["Производитель:"].get()
                supplier = self.edit_entries["Поставщик:"].get()

                if not all([article, name, category, manufacturer, supplier]):
                    messagebox.showerror("Ошибка", "Заполните все обязательные поля")
                    return

                price = float(self.edit_entries["Цена:"].get())
                discount = float(self.edit_entries["Скидка %:"].get() or 0)
                quantity = int(self.edit_entries["Количество:"].get() or 0)
                warranty = int(self.edit_entries["Гарантия (мес):"].get() or 12)
                description = self.edit_entries["Описание:"].get("1.0", tk.END).strip()

                # Получаем ID из связанных таблиц
                category_id = self.db.get_category_id(category)
                manufacturer_id = self.db.get_manufacturer_id(manufacturer)
                supplier_id = self.db.get_supplier_id(supplier)

                # Получаем ID товара
                product_id = self.db.get_product_id_by_article(product['article'])

                # Получаем старые значения для логирования
                old_product = self.db.get_product_by_id(product_id)
                old_values = {
                    'article': old_product['article'],
                    'name': old_product['name'],
                    'category': old_product['category'],
                    'manufacturer': old_product['manufacturer'],
                    'supplier': old_product['supplier'],
                    'price': float(old_product['price']),
                    'discount': float(old_product['discount']),
                    'quantity': old_product['quantity'],
                    'warranty': old_product['warranty_months']
                }

                # Обновляем в БД
                product_data = (article, name, category_id, manufacturer_id, supplier_id,
                                price, discount, quantity, description, product['photo'], warranty)

                self.db.update_product(product_id, product_data)

                # Логирование изменения товара
                self.db.log_action(
                    user_id=self.user['id'],
                    user_name=self.user['full_name'],
                    action_type='UPDATE',
                    entity_type='PRODUCT',
                    entity_id=product_id,
                    entity_details=f"Изменен товар: {name} (Артикул: {article})",
                    old_values=old_values,
                    new_values={
                        'article': article,
                        'name': name,
                        'category': category,
                        'manufacturer': manufacturer,
                        'supplier': supplier,
                        'price': price,
                        'discount': discount,
                        'quantity': quantity,
                        'warranty': warranty
                    }
                )

                messagebox.showinfo("Успех", "Товар успешно обновлен")
                edit_window.destroy()
                self.show_products()

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить изменения: {e}")

        tk.Button(btn_frame, text="Сохранить", command=save_changes,
                  bg='#00FA9A', width=15, height=2, font=("Times New Roman", 11, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(btn_frame, text="Отмена", command=edit_window.destroy,
                  bg='#FF6B6B', width=15, height=2, font=("Times New Roman", 11)).pack(side=tk.LEFT, padx=10)

        def save_changes():
            try:
                # Сбор данных из формы
                article = self.edit_entries["Артикул:"].get().strip()
                name = self.edit_entries["Наименование:"].get().strip()
                category = self.edit_entries["Категория:"].get()
                manufacturer = self.edit_entries["Производитель:"].get()
                supplier = self.edit_entries["Поставщик:"].get()

                if not all([article, name, category, manufacturer, supplier]):
                    messagebox.showerror("Ошибка", "Заполните все обязательные поля")
                    return

                price = float(self.edit_entries["Цена:"].get())
                discount = float(self.edit_entries["Скидка %:"].get() or 0)
                quantity = int(self.edit_entries["Количество:"].get() or 0)
                warranty = int(self.edit_entries["Гарантия (мес):"].get() or 12)
                description = self.edit_entries["Описание:"].get("1.0", tk.END).strip()

                # Получаем ID из связанных таблиц
                category_id = self.db.get_category_id(category)
                manufacturer_id = self.db.get_manufacturer_id(manufacturer)
                supplier_id = self.db.get_supplier_id(supplier)

                # Получаем ID товара
                product_id = self.db.get_product_id_by_article(product['article'])

                # Получаем старые значения для логирования
                old_product = self.db.get_product_by_id(product_id)
                old_values = {
                    'article': old_product['article'],
                    'name': old_product['name'],
                    'category': old_product['category'],
                    'manufacturer': old_product['manufacturer'],
                    'supplier': old_product['supplier'],
                    'price': float(old_product['price']),
                    'discount': float(old_product['discount']),
                    'quantity': old_product['quantity'],
                    'warranty': old_product['warranty_months']
                }

                # Обновляем в БД
                product_data = (article, name, category_id, manufacturer_id, supplier_id,
                                price, discount, quantity, description, product['photo'], warranty)

                self.db.update_product(product_id, product_data)

                # Логирование изменения товара
                self.db.log_action(
                    user_id=self.user['id'],
                    user_name=self.user['full_name'],
                    action_type='UPDATE',
                    entity_type='PRODUCT',
                    entity_id=product_id,
                    entity_details=f"Изменен товар: {name} (Артикул: {article})",
                    old_values=old_values,
                    new_values={
                        'article': article,
                        'name': name,
                        'category': category,
                        'manufacturer': manufacturer,
                        'supplier': supplier,
                        'price': price,
                        'discount': discount,
                        'quantity': quantity,
                        'warranty': warranty
                    }
                )

                messagebox.showinfo("Успех", "Товар успешно обновлен")
                edit_window.destroy()
                self.show_products()

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить изменения: {e}")



    def delete_product(self, product):
        """Удаление товара"""
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить товар {product['name']}?"):
            try:
                # Получаем ID товара по артикулу
                product_id = self.db.get_product_id_by_article(product['article'])
                if product_id:
                    # Получаем информацию о товаре для логирования
                    product_info = self.db.get_product_by_id(product_id)

                    # Удаляем товар
                    self.db.delete_product(product_id)

                    # Логирование удаления товара
                    self.db.log_action(
                        user_id=self.user['id'],
                        user_name=self.user['full_name'],
                        action_type='DELETE',
                        entity_type='PRODUCT',
                        entity_id=product_id,
                        entity_details=f"Удален товар: {product_info['name']} (Артикул: {product_info['article']})",
                        old_values={
                            'article': product_info['article'],
                            'name': product_info['name'],
                            'price': float(product_info['price']),
                            'quantity': product_info['quantity']
                        }
                    )

                    messagebox.showinfo("Успех", "Товар успешно удален")
                    self.show_products()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def show_my_orders(self):
        """Показывает заказы текущего пользователя"""
        self.clear_main_frame()

        title = tk.Label(self.main_frame, text="Мои заказы",
                         font=("Times New Roman", 18, "bold"), bg='#FFFFFF')
        title.pack(pady=10)

        if self.user['id'] == 0:  # Гость
            tk.Label(self.main_frame, text="Для просмотра заказов необходимо авторизоваться",
                     font=("Times New Roman", 14), bg='#FFFFFF', fg='red').pack(pady=50)
            return

        # Фильтры
        filter_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        filter_frame.pack(fill=tk.X, pady=10)

        # Статус
        tk.Label(filter_frame, text="Статус:", bg='#FFFFFF').grid(row=0, column=0, padx=5, sticky='e')
        statuses = ["Все статусы", "Новый", "В обработке", "Завершен", "Отменен"]
        self.order_status_var = tk.StringVar(value="Все статусы")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.order_status_var,
                                    values=statuses, width=15, state='readonly')
        status_combo.grid(row=0, column=1, padx=5)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.load_my_orders())

        # Поиск
        tk.Label(filter_frame, text="Поиск:", bg='#FFFFFF').grid(row=0, column=2, padx=5, sticky='e')
        self.order_search_entry = tk.Entry(filter_frame, width=30)
        self.order_search_entry.grid(row=0, column=3, padx=5)
        self.order_search_entry.bind('<KeyRelease>', lambda e: self.load_my_orders())

        # Контейнер для заказов
        orders_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        orders_frame.pack(fill=tk.BOTH, expand=True)

        self.load_my_orders(orders_frame)

    def load_my_orders(self, parent_frame=None):
        """Загрузка заказов текущего пользователя"""
        if parent_frame is None:
            parent_frame = self.main_frame

        for widget in parent_frame.winfo_children():
            if isinstance(widget, tk.Frame) and widget != parent_frame:
                widget.destroy()

        # Получаем заказы с фильтрацией
        filters = {
            'status': self.order_status_var.get() if hasattr(self, 'order_status_var') else "Все статусы",
            'search': self.order_search_entry.get() if hasattr(self, 'order_search_entry') else "",
            'user_id': self.user['id']
        }

        orders = self.db.get_orders(filters)

        if not orders:
            tk.Label(parent_frame, text="У вас пока нет заказов",
                     font=("Times New Roman", 14), bg='#FFFFFF').pack(pady=50)
            return

        # Создаем таблицу заказов
        columns = ("Номер заказа", "Дата", "Дата доставки", "Пункт выдачи", "Статус", "Код получения")
        tree = ttk.Treeview(parent_frame, columns=columns, show="headings", height=15)

        # Настройка колонок
        col_widths = [120, 90, 90, 300, 100, 100]
        for col, width in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, minwidth=width)

        # Добавляем заказы
        for order in orders:
            item_id = tree.insert("", "end", values=(
                order['order_number'],
                order['order_date'].strftime("%d.%m.%Y"),
                order['delivery_date'].strftime("%d.%m.%Y") if order['delivery_date'] else "",
                order['address'],
                order['status'],
                order['pickup_code'] or ""
            ))

            # Сохраняем ID заказа для просмотра деталей
            tree.item(item_id, tags=(str(order['id']),))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Добавляем скроллбар
        scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        # Обработчик двойного клика
        def on_double_click(event):
            item = tree.selection()[0]
            order_id = tree.item(item, "tags")[0]
            order = next((o for o in orders if str(o['id']) == order_id), None)
            if order:
                self.show_order_details(order)

        tree.bind('<Double-1>', on_double_click)

    def show_all_orders(self):
        """Показывает все заказы (для менеджеров и администраторов)"""
        self.clear_main_frame()

        title = tk.Label(self.main_frame, text="Все заказы",
                         font=("Times New Roman", 18, "bold"), bg='#FFFFFF')
        title.pack(pady=10)

        # Фильтры
        filter_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        filter_frame.pack(fill=tk.X, pady=10)

        # Статус
        tk.Label(filter_frame, text="Статус:", bg='#FFFFFF').grid(row=0, column=0, padx=5, sticky='e')
        statuses = ["Все статусы", "Новый", "В обработке", "Завершен", "Отменен"]
        self.all_orders_status_var = tk.StringVar(value="Все статусы")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.all_orders_status_var,
                                    values=statuses, width=15, state='readonly')
        status_combo.grid(row=0, column=1, padx=5)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.load_all_orders())

        # Поиск
        tk.Label(filter_frame, text="Поиск:", bg='#FFFFFF').grid(row=0, column=2, padx=5, sticky='e')
        self.all_orders_search_entry = tk.Entry(filter_frame, width=30)
        self.all_orders_search_entry.grid(row=0, column=3, padx=5)
        self.all_orders_search_entry.bind('<KeyRelease>', lambda e: self.load_all_orders())

        # Дата с
        tk.Label(filter_frame, text="Дата с:", bg='#FFFFFF').grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.date_from_entry = tk.Entry(filter_frame, width=12)
        self.date_from_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.date_from_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))

        # Дата по
        tk.Label(filter_frame, text="по:", bg='#FFFFFF').grid(row=1, column=2, padx=5, pady=5, sticky='e')
        self.date_to_entry = tk.Entry(filter_frame, width=12)
        self.date_to_entry.grid(row=1, column=3, padx=5, pady=5, sticky='w')
        self.date_to_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # Кнопка применения фильтров
        apply_btn = tk.Button(filter_frame, text="Применить фильтры",
                              command=self.load_all_orders, bg='#00FA9A')
        apply_btn.grid(row=1, column=4, padx=20)

        # Контейнер для заказов
        self.all_orders_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        self.all_orders_frame.pack(fill=tk.BOTH, expand=True)

        self.load_all_orders()

    def load_all_orders(self):
        """Загрузка всех заказов с фильтрацией"""
        for widget in self.all_orders_frame.winfo_children():
            widget.destroy()

        # Получаем заказы с фильтрацией
        try:
            filters = {
                'status': self.all_orders_status_var.get(),
                'search': self.all_orders_search_entry.get(),
                'date_from': self.date_from_entry.get(),
                'date_to': self.date_to_entry.get()
            }
        except:
            filters = {}

        orders = self.db.get_orders(filters)

        if not orders:
            tk.Label(self.all_orders_frame, text="Заказы не найдены",
                     font=("Times New Roman", 14), bg='#FFFFFF').pack(pady=50)
            return

        # Создаем таблицу заказов
        columns = ("Номер", "Дата", "Клиент", "Пункт выдачи", "Статус", "Код")
        tree = ttk.Treeview(self.all_orders_frame, columns=columns, show="headings", height=20)

        # Настройка колонок
        col_widths = [120, 90, 180, 300, 100, 70]
        for col, width in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, minwidth=width)

        # Добавляем заказы
        for order in orders:
            item_id = tree.insert("", "end", values=(
                order['order_number'],
                order['order_date'].strftime("%d.%m.%Y"),
                order['full_name'],
                order['address'],
                order['status'],
                order['pickup_code'] or ""
            ))

            # Сохраняем ID заказа для просмотра деталей
            tree.item(item_id, tags=(str(order['id']),))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Добавляем скроллбар
        scrollbar = tk.Scrollbar(self.all_orders_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        # Обработчик двойного клика
        def on_double_click(event):
            item = tree.selection()[0]
            order_id = tree.item(item, "tags")[0]
            order = next((o for o in orders if str(o['id']) == order_id), None)
            if order:
                self.show_order_details(order)

        tree.bind('<Double-1>', on_double_click)

    def show_order_details(self, order):
        """Показывает детали заказа"""
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Детали заказа №{order['order_number']}")
        details_window.geometry("700x600")
        details_window.configure(bg='#FFFFFF')

        # Центрируем окно
        details_window.update_idletasks()
        width = details_window.winfo_width()
        height = details_window.winfo_height()
        x = (details_window.winfo_screenwidth() // 2) - (width // 2)
        y = (details_window.winfo_screenheight() // 2) - (height // 2)
        details_window.geometry(f'{width}x{height}+{x}+{y}')

        # Заголовок
        tk.Label(details_window, text=f"Заказ №{order['order_number']}",
                 font=("Times New Roman", 18, "bold"), bg='#FFFFFF').pack(pady=10)

        # Информация о заказе
        info_frame = tk.Frame(details_window, bg='#F0F0F0', relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        # Статус с цветом
        status_colors = {
            'Новый': '#FFA500',
            'В обработке': '#4169E1',
            'Завершен': '#2E8B57',
            'Отменен': '#FF0000'
        }
        status_color = status_colors.get(order['status'], '#808080')

        status_label = tk.Label(info_frame, text=f"Статус: {order['status']}",
                                font=("Times New Roman", 12, "bold"),
                                bg=status_color, fg='white', padx=10, pady=5)
        status_label.pack(anchor='w', padx=10, pady=5)

        info_text = f"""
        Дата заказа: {order['order_date'].strftime('%d.%m.%Y')}
        Дата доставки: {order['delivery_date'].strftime('%d.%m.%Y') if order['delivery_date'] else 'Не указана'}
        Пункт выдачи: {order['address']}
        Клиент: {order['full_name']}
        Код получения: {order['pickup_code']}
        """

        tk.Label(info_frame, text=info_text, bg='#F0F0F0', justify=tk.LEFT,
                 font=("Times New Roman", 11)).pack(padx=10, pady=10)

        # Состав заказа
        tk.Label(details_window, text="Состав заказа:",
                 font=("Times New Roman", 14, "bold"), bg='#FFFFFF').pack(pady=10)

        # Получаем детали заказа
        items = self.db.get_order_details(order['id'])

        if items:
            # Таблица товаров
            frame = tk.Frame(details_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=20)

            columns = ("Артикул", "Наименование", "Количество", "Цена", "Сумма")
            tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)

            col_widths = [100, 300, 80, 100, 100]
            for col, width in zip(columns, col_widths):
                tree.heading(col, text=col)
                tree.column(col, width=width)

            total_sum = 0
            for item in items:
                price = float(item['price_at_order'])
                sum_price = price * item['quantity']
                total_sum += sum_price

                tree.insert("", "end", values=(
                    item['article'],
                    item['name'],
                    item['quantity'],
                    self.format_price(price),
                    self.format_price(sum_price)
                ))

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Скроллбар
            scrollbar = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.configure(yscrollcommand=scrollbar.set)

            # Итоговая сумма
            tk.Label(details_window, text=f"ИТОГО: {self.format_price(total_sum)}",
                     font=("Times New Roman", 16, "bold"), bg='#FFFFFF',
                     fg='#2E8B57').pack(pady=10)
        else:
            tk.Label(details_window, text="Состав заказа не найден",
                     bg='#FFFFFF').pack()

        # Кнопки действий для менеджеров и администраторов
        if self.user['role_name'] in ['Менеджер', 'Администратор']:
            btn_frame = tk.Frame(details_window, bg='#FFFFFF')
            btn_frame.pack(pady=20)

            # Кнопка редактирования
            edit_btn = tk.Button(btn_frame, text="✏️ Редактировать",
                                 command=lambda: self.edit_order(order),
                                 bg='#00FA9A', width=15)
            edit_btn.pack(side=tk.LEFT, padx=5)

            # Кнопка удаления (только для администраторов)
            if self.user['role_name'] == 'Администратор':
                delete_btn = tk.Button(btn_frame, text="🗑️ Удалить",
                                       command=lambda: self.delete_order(order['id'], details_window),
                                       bg='#FF6B6B', width=15)
                delete_btn.pack(side=tk.LEFT, padx=5)

        # Кнопка закрытия
        tk.Button(details_window, text="Закрыть", command=details_window.destroy,
                  bg='#7FFF00', width=15).pack(pady=10)

    def edit_order(self, order):
        """Редактирование заказа"""
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Редактирование заказа №{order['order_number']}")
        edit_window.geometry("800x600")
        edit_window.configure(bg='#FFFFFF')

        # Центрируем окно
        edit_window.update_idletasks()
        width = edit_window.winfo_width()
        height = edit_window.winfo_height()
        x = (edit_window.winfo_screenwidth() // 2) - (width // 2)
        y = (edit_window.winfo_screenheight() // 2) - (height // 2)
        edit_window.geometry(f'{width}x{height}+{x}+{y}')

        # Заголовок
        tk.Label(edit_window, text=f"Редактирование заказа №{order['order_number']}",
                 font=("Times New Roman", 16, "bold"), bg='#FFFFFF').pack(pady=10)

        # Основная информация
        info_frame = tk.Frame(edit_window, bg='#F0F0F0', relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        # Дата доставки
        date_frame = tk.Frame(info_frame, bg='#F0F0F0')
        date_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(date_frame, text="Дата доставки:", bg='#F0F0F0').pack(side=tk.LEFT)

        dates = []
        for i in range(1, 15):
            date = datetime.now() + timedelta(days=i)
            dates.append(date.strftime('%Y-%m-%d'))

        self.edit_delivery_var = tk.StringVar(
            value=order['delivery_date'].strftime('%Y-%m-%d') if order['delivery_date'] else dates[0])
        delivery_combo = ttk.Combobox(date_frame, textvariable=self.edit_delivery_var,
                                      values=dates, width=15, state='readonly')
        delivery_combo.pack(side=tk.LEFT, padx=10)

        # Статус
        status_frame = tk.Frame(info_frame, bg='#F0F0F0')
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(status_frame, text="Статус:", bg='#F0F0F0').pack(side=tk.LEFT)

        statuses = ["Новый", "В обработке", "Завершен", "Отменен"]
        self.edit_status_var = tk.StringVar(value=order['status'])
        status_combo = ttk.Combobox(status_frame, textvariable=self.edit_status_var,
                                    values=statuses, width=15, state='readonly')
        status_combo.pack(side=tk.LEFT, padx=10)

        # Состав заказа
        tk.Label(edit_window, text="Состав заказа:",
                 font=("Times New Roman", 12, "bold"), bg='#FFFFFF').pack(pady=10)

        # Получаем текущие товары в заказе
        items = self.db.get_order_details(order['id'])

        # Таблица для отображения и редактирования состава
        items_frame = tk.Frame(edit_window)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        columns = ("Артикул", "Наименование", "Количество", "Цена", "Сумма", "Действия")
        tree = ttk.Treeview(items_frame, columns=columns, show="headings", height=8)

        col_widths = [100, 300, 80, 100, 100, 80]
        for col, width in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width)

        # Заполняем текущими товарами
        self.edit_items = []
        total_sum = 0

        for item in items:
            price = float(item['price_at_order'])
            sum_price = price * item['quantity']
            total_sum += sum_price

            item_id = tree.insert("", "end", values=(
                item['article'],
                item['name'],
                item['quantity'],
                self.format_price(price),
                self.format_price(sum_price),
                "❌"
            ))

            self.edit_items.append({
                'product_id': item['product_id'],
                'article': item['article'],
                'name': item['name'],
                'quantity': item['quantity'],
                'price': price
            })
            tree.item(item_id, tags=(str(len(self.edit_items) - 1),))

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Скроллбар
        scrollbar = tk.Scrollbar(items_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        # Обработчик удаления товара из заказа
        def on_delete_click(event):
            item = tree.selection()[0]
            idx = int(tree.item(item, "tags")[0])
            if messagebox.askyesno("Подтверждение", "Удалить товар из заказа?"):
                tree.delete(item)
                del self.edit_items[idx]
                # Пересчет итога
                self.update_edit_total()

        tree.bind('<Double-1>', on_delete_click)

        # Кнопка добавления товара
        add_frame = tk.Frame(edit_window, bg='#FFFFFF')
        add_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Button(add_frame, text="+ Добавить товар",
                  command=lambda: self.add_item_to_edit_order(edit_window, tree),
                  bg='#00FA9A', width=15).pack(side=tk.LEFT)

        # Итоговая сумма
        self.edit_total_label = tk.Label(edit_window,
                                         text=f"ИТОГО: {self.format_price(total_sum)}",
                                         font=("Times New Roman", 14, "bold"),
                                         bg='#FFFFFF', fg='#2E8B57')
        self.edit_total_label.pack(pady=10)

        # Кнопки сохранения
        btn_frame = tk.Frame(edit_window, bg='#FFFFFF')
        btn_frame.pack(pady=20)

        def save_order_changes():
            try:
                # Подготовка данных заказа
                order_data = {
                    'delivery_date': datetime.strptime(self.edit_delivery_var.get(), '%Y-%m-%d').date(),
                    'pickup_point_id': order['pickup_point_id'],
                    'status': self.edit_status_var.get()
                }

                # Подготовка позиций
                items_data = []
                total_sum = 0
                for item in self.edit_items:
                    items_data.append({
                        'product_id': item['product_id'],
                        'quantity': item['quantity'],
                        'price': item['price']
                    })
                    total_sum += item['price'] * item['quantity']

                # Получаем старые значения для логирования
                old_status = order['status']
                old_delivery = order['delivery_date'].strftime('%Y-%m-%d') if order['delivery_date'] else ""

                # Обновляем заказ
                self.db.update_order(order['id'], order_data, items_data)

                # Логирование изменения заказа
                self.db.log_action(
                    user_id=self.user['id'],
                    user_name=self.user['full_name'],
                    action_type='UPDATE',
                    entity_type='ORDER',
                    entity_id=order['id'],
                    entity_details=f"Изменен заказ №{order['order_number']}",
                    old_values={
                        'status': old_status,
                        'delivery_date': old_delivery
                    },
                    new_values={
                        'status': order_data['status'],
                        'delivery_date': str(order_data['delivery_date']),
                        'items_count': len(items_data),
                        'total': total_sum
                    }
                )

                messagebox.showinfo("Успех", "Заказ успешно обновлен")
                edit_window.destroy()
                self.show_all_orders()

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось обновить заказ: {e}")

        tk.Button(btn_frame, text="Сохранить изменения", command=save_order_changes,
                  bg='#00FA9A', width=20, height=2, font=("Times New Roman", 11, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(btn_frame, text="Отмена", command=edit_window.destroy,
                  bg='#FF6B6B', width=15, height=2).pack(side=tk.LEFT, padx=10)

    def add_item_to_edit_order(self, parent_window, tree):
        """Добавление товара в редактируемый заказ"""
        add_window = tk.Toplevel(parent_window)
        add_window.title("Добавление товара")
        add_window.geometry("500x300")
        add_window.configure(bg='#FFFFFF')

        # Центрируем окно
        add_window.update_idletasks()
        width = add_window.winfo_width()
        height = add_window.winfo_height()
        x = (add_window.winfo_screenwidth() // 2) - (width // 2)
        y = (add_window.winfo_screenheight() // 2) - (height // 2)
        add_window.geometry(f'{width}x{height}+{x}+{y}')

        tk.Label(add_window, text="Выберите товар",
                 font=("Times New Roman", 14, "bold"), bg='#FFFFFF').pack(pady=10)

        # Поиск товара
        search_frame = tk.Frame(add_window, bg='#FFFFFF')
        search_frame.pack(pady=10)

        tk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT)
        search_entry = tk.Entry(search_frame, width=30)
        search_entry.pack(side=tk.LEFT, padx=10)

        # Список товаров
        list_frame = tk.Frame(add_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        # Получаем все товары
        products = self.db.get_all_products()

        # Создаем список для выбора
        listbox = tk.Listbox(list_frame, height=10)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

        # Заполняем список
        product_items = []
        for p in products:
            if p['quantity'] > 0:  # Только товары в наличии
                display_text = f"{p['article']} - {p['name']} - {self.format_price(p['price'])}"
                listbox.insert(tk.END, display_text)
                product_items.append(p)

        # Количество
        qty_frame = tk.Frame(add_window, bg='#FFFFFF')
        qty_frame.pack(pady=10)

        tk.Label(qty_frame, text="Количество:").pack(side=tk.LEFT)
        qty_var = tk.StringVar(value="1")
        qty_spinbox = tk.Spinbox(qty_frame, from_=1, to=100, textvariable=qty_var, width=10)
        qty_spinbox.pack(side=tk.LEFT, padx=10)

        def add_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Ошибка", "Выберите товар")
                return

            idx = selection[0]
            product = product_items[idx]
            quantity = int(qty_var.get())

            if quantity > product['quantity']:
                messagebox.showerror("Ошибка", f"Доступно только {product['quantity']} шт.")
                return

            # Добавляем в список редактирования
            price = float(product['price'])
            discount = float(product['discount'])
            final_price = price * (1 - discount / 100) if discount > 0 else price

            self.edit_items.append({
                'product_id': self.db.get_product_id_by_article(product['article']),
                'article': product['article'],
                'name': product['name'],
                'quantity': quantity,
                'price': final_price
            })

            # Обновляем таблицу
            sum_price = final_price * quantity
            tree.insert("", "end", values=(
                product['article'],
                product['name'],
                quantity,
                self.format_price(final_price),
                self.format_price(sum_price),
                "❌"
            ))

            # Обновляем итог
            self.update_edit_total()

            add_window.destroy()

        tk.Button(add_window, text="Добавить", command=add_selected,
                  bg='#00FA9A', width=15).pack(pady=10)

    def update_edit_total(self):
        """Обновление итоговой суммы при редактировании заказа"""
        total = 0
        for item in self.edit_items:
            total += item['price'] * item['quantity']
        self.edit_total_label.config(text=f"ИТОГО: {self.format_price(total)}")

    def update_order_status(self, order_id, new_status, window):
        """Обновление статуса заказа"""
        try:
            # Получаем информацию о заказе
            orders = self.db.get_orders({'order_id': order_id})
            if orders:
                order_info = orders[0]
                old_status = order_info['status']

                # Обновляем статус
                old_data = self.db.update_order_status(order_id, new_status)

                # Логирование изменения статуса
                self.db.log_action(
                    user_id=self.user['id'],
                    user_name=self.user['full_name'],
                    action_type='UPDATE',
                    entity_type='ORDER',
                    entity_id=order_id,
                    entity_details=f"Изменен статус заказа №{order_info['order_number']}: {old_status} -> {new_status}",
                    old_values={'status': old_status},
                    new_values={'status': new_status}
                )

                messagebox.showinfo("Успех", "Статус заказа обновлен")
                window.destroy()
                # Обновляем список заказов
                if hasattr(self, 'all_orders_frame'):
                    self.load_all_orders()
                else:
                    self.show_all_orders()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить статус: {e}")

    def delete_order(self, order_id, window):
        """Удаление заказа"""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить заказ?"):
            try:
                # Получаем информацию о заказе для логирования
                orders = self.db.get_orders({'order_id': order_id})
                if orders:
                    order_info = orders[0]

                    # Удаляем заказ
                    self.db.delete_order(order_id)

                    # Логирование удаления заказа
                    self.db.log_action(
                        user_id=self.user['id'],
                        user_name=self.user['full_name'],
                        action_type='DELETE',
                        entity_type='ORDER',
                        entity_id=order_id,
                        entity_details=f"Удален заказ №{order_info['order_number']}",
                        old_values={
                            'order_number': order_info['order_number'],
                            'status': order_info['status'],
                            'user': order_info['full_name']
                        }
                    )

                    messagebox.showinfo("Успех", "Заказ удален")
                    window.destroy()
                    self.show_all_orders()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить заказ: {e}")

    def add_product(self):
        self.clear_main_frame()

        title = tk.Label(self.main_frame, text="Добавление товара",
                         font=("Times New Roman", 18, "bold"), bg='#FFFFFF')
        title.pack(pady=10)

        # Форма добавления
        form_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        form_frame.pack(pady=20)

        fields = [
            ("Артикул:", "entry"),
            ("Наименование:", "entry"),
            ("Категория:", "combo", [cat[1] for cat in self.db.get_categories()]),
            ("Производитель:", "combo", [man[1] for man in self.db.get_manufacturers()]),
            ("Поставщик:", "combo", [sup[1] for sup in self.db.get_suppliers()]),
            ("Цена:", "entry"),
            ("Скидка %:", "entry"),
            ("Количество:", "entry"),
            ("Описание:", "text"),
            ("Гарантия (мес):", "entry")
        ]

        self.product_entries = {}

        for i, field_info in enumerate(fields):
            label_text = field_info[0]
            field_type = field_info[1]

            tk.Label(form_frame, text=label_text, bg='#FFFFFF', font=("Times New Roman", 11)).grid(
                row=i, column=0, pady=5, padx=5, sticky='e')

            if field_type == "entry":
                entry = tk.Entry(form_frame, width=40, font=("Times New Roman", 11))
                entry.grid(row=i, column=1, pady=5, padx=5)
                self.product_entries[label_text] = entry
            elif field_type == "combo":
                values = field_info[2] if len(field_info) > 2 else []
                var = tk.StringVar()
                combo = ttk.Combobox(form_frame, textvariable=var, values=values,
                                     width=38, font=("Times New Roman", 11), state='readonly')
                combo.grid(row=i, column=1, pady=5, padx=5)
                self.product_entries[label_text] = var
            elif field_type == "text":
                text_frame = tk.Frame(form_frame)
                text_frame.grid(row=i, column=1, pady=5, padx=5)
                text = tk.Text(text_frame, width=40, height=5, font=("Times New Roman", 11))
                text.pack(side=tk.LEFT)
                scrollbar = tk.Scrollbar(text_frame, command=text.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                text.config(yscrollcommand=scrollbar.set)
                self.product_entries[label_text] = text

        # Кнопка сохранения
        btn_frame = tk.Frame(form_frame, bg='#FFFFFF')
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)

        save_btn = tk.Button(btn_frame, text="Сохранить", command=self.save_product,
                             bg='#00FA9A', width=15, height=2, font=("Times New Roman", 11, "bold"))
        save_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = tk.Button(btn_frame, text="Отмена", command=self.show_products,
                               bg='#FF6B6B', width=15, height=2, font=("Times New Roman", 11))
        cancel_btn.pack(side=tk.LEFT, padx=10)

    def save_product(self):
        try:
            # Сбор данных из формы
            article = self.product_entries["Артикул:"].get().strip()
            name = self.product_entries["Наименование:"].get().strip()
            category = self.product_entries["Категория:"].get()
            manufacturer = self.product_entries["Производитель:"].get()
            supplier = self.product_entries["Поставщик:"].get()

            # Проверка обязательных полей
            if not all([article, name, category, manufacturer, supplier]):
                messagebox.showerror("Ошибка", "Заполните все обязательные поля")
                return

            # Получаем цену
            price_str = self.product_entries["Цена:"].get().strip()
            if not price_str:
                messagebox.showerror("Ошибка", "Введите цену")
                return
            try:
                price = float(price_str)
                if price <= 0 or price > 999999.99:
                    messagebox.showerror("Ошибка", "Цена должна быть от 0 до 999999.99")
                    return
            except ValueError:
                messagebox.showerror("Ошибка", "Некорректное значение цены")
                return

            # Получаем скидку
            discount_str = self.product_entries["Скидка %:"].get().strip()
            try:
                discount = float(discount_str) if discount_str else 0
                if discount < 0 or discount > 100:
                    messagebox.showerror("Ошибка", "Скидка должна быть от 0 до 100")
                    return
            except ValueError:
                discount = 0

            # Получаем количество
            quantity_str = self.product_entries["Количество:"].get().strip()
            try:
                quantity = int(quantity_str) if quantity_str else 0
                if quantity < 0:
                    messagebox.showerror("Ошибка", "Количество не может быть отрицательным")
                    return
            except ValueError:
                quantity = 0

            # Получаем описание
            description = self.product_entries["Описание:"].get("1.0", tk.END).strip()

            # Получаем гарантию
            warranty_str = self.product_entries["Гарантия (мес):"].get().strip()
            try:
                warranty = int(warranty_str) if warranty_str else 12
                if warranty < 0:
                    messagebox.showerror("Ошибка", "Гарантия не может быть отрицательной")
                    return
            except ValueError:
                warranty = 12

            # Получаем ID из связанных таблиц
            category_id = self.db.get_category_id(category)
            manufacturer_id = self.db.get_manufacturer_id(manufacturer)
            supplier_id = self.db.get_supplier_id(supplier)

            if not all([category_id, manufacturer_id, supplier_id]):
                messagebox.showerror("Ошибка", "Не найдены соответствующие записи в справочниках")
                return

            # Сохраняем в БД
            product_data = (article, name, category_id, manufacturer_id, supplier_id,
                            price, discount, quantity, description, "", warranty)

            product_id = self.db.add_product(product_data)

            # Логирование создания товара
            self.db.log_action(
                user_id=self.user['id'],
                user_name=self.user['full_name'],
                action_type='CREATE',
                entity_type='PRODUCT',
                entity_id=product_id,
                entity_details=f"Добавлен товар: {name} (Артикул: {article})",
                new_values={
                    'article': article,
                    'name': name,
                    'category': category,
                    'manufacturer': manufacturer,
                    'supplier': supplier,
                    'price': price,
                    'discount': discount,
                    'quantity': quantity,
                    'warranty': warranty
                }
            )

            messagebox.showinfo("Успех", "Товар успешно добавлен")
            self.show_products()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить товар: {e}")

            # Добавьте этот метод в класс MainApp после метода manage_orders
    def create_new_order(self):
        """Создание нового заказа"""
        self.clear_main_frame()

        title = tk.Label(self.main_frame, text="Создание нового заказа",
                         font=("Times New Roman", 18, "bold"), bg='#FFFFFF')
        title.pack(pady=10)

        # Основной контейнер
        main_container = tk.Frame(self.main_frame, bg='#FFFFFF')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Левая часть - выбор товаров
        left_frame = tk.Frame(main_container, bg='#FFFFFF', relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(left_frame, text="Выберите товары", font=("Times New Roman", 14, "bold"),
                 bg='#FFFFFF').pack(pady=10)

        # Поиск товаров
        search_frame = tk.Frame(left_frame, bg='#FFFFFF')
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="Поиск:", bg='#FFFFFF').pack(side=tk.LEFT)
        self.new_order_search = tk.Entry(search_frame, width=40)
        self.new_order_search.pack(side=tk.LEFT, padx=10)
        self.new_order_search.bind('<KeyRelease>', lambda e: self.load_products_for_order())

        # Фильтр категорий
        filter_frame = tk.Frame(left_frame, bg='#FFFFFF')
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(filter_frame, text="Категория:", bg='#FFFFFF').pack(side=tk.LEFT)
        categories = ["Все категории"] + [cat[1] for cat in self.db.get_categories()]
        self.new_order_category = tk.StringVar(value="Все категории")
        category_combo = ttk.Combobox(filter_frame, textvariable=self.new_order_category,
                                      values=categories, width=30, state='readonly')
        category_combo.pack(side=tk.LEFT, padx=10)
        category_combo.bind('<<ComboboxSelected>>', lambda e: self.load_products_for_order())

        # Список товаров
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Создаем Treeview для товаров
        columns = ("Артикул", "Наименование", "Цена", "Скидка", "В наличии")
        self.products_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        col_widths = [100, 250, 100, 70, 70]
        for col, width in zip(columns, col_widths):
            self.products_tree.heading(col, text=col)
            self.products_tree.column(col, width=width)

        self.products_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Скроллбар
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.products_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.products_tree.configure(yscrollcommand=scrollbar.set)

        # Кнопка добавления товара
        add_btn_frame = tk.Frame(left_frame, bg='#FFFFFF')
        add_btn_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(add_btn_frame, text="Количество:", bg='#FFFFFF').pack(side=tk.LEFT)
        self.new_order_quantity = tk.Spinbox(add_btn_frame, from_=1, to=100, width=10)
        self.new_order_quantity.pack(side=tk.LEFT, padx=10)

        tk.Button(add_btn_frame, text="Добавить в заказ", command=self.add_to_new_order,
                  bg='#00FA9A', width=15).pack(side=tk.LEFT, padx=10)

        # Правая часть - состав заказа
        right_frame = tk.Frame(main_container, bg='#F0F0F0', relief=tk.RAISED, bd=2, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="Состав заказа", font=("Times New Roman", 14, "bold"),
                 bg='#F0F0F0').pack(pady=10)

        # Таблица состава заказа
        order_items_frame = tk.Frame(right_frame)
        order_items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns2 = ("Наименование", "Кол-во", "Цена", "Сумма", "")
        self.order_items_tree = ttk.Treeview(order_items_frame, columns=columns2, show="headings", height=10)

        col2_widths = [200, 50, 80, 80, 30]
        for col, width in zip(columns2, col2_widths):
            self.order_items_tree.heading(col, text=col)
            self.order_items_tree.column(col, width=width)

        self.order_items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Скроллбар
        scrollbar2 = tk.Scrollbar(order_items_frame, orient="vertical", command=self.order_items_tree.yview)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        self.order_items_tree.configure(yscrollcommand=scrollbar2.set)

        # Информация о заказе
        info_frame = tk.Frame(right_frame, bg='#F0F0F0')
        info_frame.pack(fill=tk.X, padx=10, pady=10)

        # Клиент
        tk.Label(info_frame, text="Клиент:", bg='#F0F0F0').pack(anchor='w', pady=2)

        # Получаем список клиентов
        cursor = self.db.connection.cursor(dictionary=True)
        cursor.execute("SELECT id, full_name FROM users WHERE role_id = 3")  # role_id 3 = клиент
        clients = cursor.fetchall()
        client_names = [c['full_name'] for c in clients]

        self.new_order_client = tk.StringVar()
        client_combo = ttk.Combobox(info_frame, textvariable=self.new_order_client,
                                    values=client_names, width=35, state='readonly')
        client_combo.pack(fill=tk.X, pady=2)
        if client_names:
            client_combo.current(0)

        # Пункт выдачи
        tk.Label(info_frame, text="Пункт выдачи:", bg='#F0F0F0').pack(anchor='w', pady=2)

        pickup_points = self.db.get_pickup_points()
        pickup_addresses = [p['address'] for p in pickup_points]

        self.new_order_pickup = tk.StringVar()
        pickup_combo = ttk.Combobox(info_frame, textvariable=self.new_order_pickup,
                                    values=pickup_addresses, width=35, state='readonly')
        pickup_combo.pack(fill=tk.X, pady=2)
        if pickup_addresses:
            pickup_combo.current(0)

        # Дата доставки
        tk.Label(info_frame, text="Дата доставки:", bg='#F0F0F0').pack(anchor='w', pady=2)

        dates = []
        for i in range(1, 15):
            date = datetime.now() + timedelta(days=i)
            dates.append(date.strftime('%Y-%m-%d'))

        self.new_order_delivery = tk.StringVar(value=dates[0])
        delivery_combo = ttk.Combobox(info_frame, textvariable=self.new_order_delivery,
                                      values=dates, width=20, state='readonly')
        delivery_combo.pack(anchor='w', pady=2)

        # Итоговая сумма
        self.new_order_total = tk.Label(info_frame, text="ИТОГО: 0 ₽",
                                        font=("Times New Roman", 14, "bold"),
                                        bg='#F0F0F0', fg='#2E8B57')
        self.new_order_total.pack(pady=10)

        # Кнопки
        btn_frame = tk.Frame(right_frame, bg='#F0F0F0')
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Создать заказ", command=self.save_new_order,
                  bg='#00FA9A', width=20, height=2, font=("Times New Roman", 11, "bold")).pack(pady=5)

        tk.Button(btn_frame, text="Очистить", command=self.clear_new_order,
                  bg='#FFA500', width=20).pack(pady=5)

        tk.Button(btn_frame, text="Отмена", command=self.show_all_orders,
                  bg='#FF6B6B', width=20).pack(pady=5)

        # Инициализируем список товаров в заказе
        self.new_order_items = []

        # Загружаем товары
        self.load_products_for_order()

    def load_products_for_order(self):
        """Загрузка товаров для выбора в новом заказе"""
        # Очищаем текущий список
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)

        # Получаем товары с фильтрацией
        search_text = self.new_order_search.get() if hasattr(self, 'new_order_search') else ""
        category = self.new_order_category.get() if hasattr(self, 'new_order_category') else "Все категории"

        products = self.db.get_filtered_products(search_text, category, "", "name")

        # Заполняем список
        self.available_products = []
        for product in products:
            if product['quantity'] > 0:  # Только товары в наличии
                price = float(product['price'])
                discount = float(product['discount'])
                final_price = price * (1 - discount / 100) if discount > 0 else price

                self.products_tree.insert("", "end", values=(
                    product['article'],
                    product['name'],
                    self.format_price(final_price),
                    f"{discount:.0f}%" if discount > 0 else "-",
                    product['quantity']
                ))
                self.available_products.append(product)

    def add_to_new_order(self):
        """Добавление товара в новый заказ"""
        selection = self.products_tree.selection()
        if not selection:
            messagebox.showwarning("Ошибка", "Выберите товар")
            return

        # Получаем выбранный товар
        item = selection[0]
        values = self.products_tree.item(item, "values")
        article = values[0]

        # Находим полную информацию о товаре
        product = None
        for p in self.available_products:
            if p['article'] == article:
                product = p
                break

        if not product:
            return

        # Получаем количество
        try:
            quantity = int(self.new_order_quantity.get())
            if quantity <= 0:
                messagebox.showerror("Ошибка", "Количество должно быть больше 0")
                return
            if quantity > product['quantity']:
                messagebox.showerror("Ошибка", f"Доступно только {product['quantity']} шт.")
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректное количество")
            return

        # Проверяем, нет ли уже такого товара в заказе
        for item in self.new_order_items:
            if item['article'] == article:
                if messagebox.askyesno("Подтверждение",
                                       f"Товар уже добавлен. Добавить еще {quantity} шт.?"):
                    item['quantity'] += quantity
                    self.update_order_items_display()
                return

        # Добавляем товар
        price = float(product['price'])
        discount = float(product['discount'])
        final_price = price * (1 - discount / 100) if discount > 0 else price

        self.new_order_items.append({
            'product_id': self.db.get_product_id_by_article(article),
            'article': article,
            'name': product['name'],
            'quantity': quantity,
            'price': final_price
        })

        self.update_order_items_display()

    def update_order_items_display(self):
        """Обновление отображения состава заказа"""
        # Очищаем текущий список
        for item in self.order_items_tree.get_children():
            self.order_items_tree.delete(item)

        # Добавляем товары
        total = 0
        for i, item in enumerate(self.new_order_items):
            sum_price = item['price'] * item['quantity']
            total += sum_price

            item_id = self.order_items_tree.insert("", "end", values=(
                item['name'],
                item['quantity'],
                self.format_price(item['price']),
                self.format_price(sum_price),
                "❌"
            ))
            self.order_items_tree.item(item_id, tags=(str(i),))

        # Обновляем итог
        self.new_order_total.config(text=f"ИТОГО: {self.format_price(total)}")

    def save_new_order(self):
        """Сохранение нового заказа"""
        # Проверка наличия товаров
        if not self.new_order_items:
            messagebox.showwarning("Ошибка", "Добавьте товары в заказ")
            return

        # Проверка клиента
        if not self.new_order_client.get():
            messagebox.showwarning("Ошибка", "Выберите клиента")
            return

        # Проверка пункта выдачи
        if not self.new_order_pickup.get():
            messagebox.showwarning("Ошибка", "Выберите пункт выдачи")
            return

        # Проверка даты доставки
        if not self.new_order_delivery.get():
            messagebox.showwarning("Ошибка", "Выберите дату доставки")
            return

        try:
            # Получаем ID клиента
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT id FROM users WHERE full_name = %s",
                           (self.new_order_client.get(),))
            client_id = cursor.fetchone()[0]

            # Получаем ID пункта выдачи
            pickup_point_id = self.db.get_pickup_point_by_address(self.new_order_pickup.get())

            # Подготовка данных заказа
            order_number = self.db.generate_order_number()
            order_date = datetime.now().date()
            delivery_date = datetime.strptime(self.new_order_delivery.get(), '%Y-%m-%d').date()
            pickup_code = self.db.generate_pickup_code()
            status = "Новый"

            order_data = (order_number, order_date, delivery_date, pickup_point_id,
                          client_id, pickup_code, status)

            # Подготовка позиций
            items_data = []
            total_sum = 0
            for item in self.new_order_items:
                items_data.append({
                    'product_id': item['product_id'],
                    'quantity': item['quantity'],
                    'price': item['price']
                })
                total_sum += item['price'] * item['quantity']

            # Создаем заказ
            order_id = self.db.create_order(order_data, items_data)

            # Логирование создания заказа
            self.db.log_action(
                user_id=self.user['id'],
                user_name=self.user['full_name'],
                action_type='CREATE',
                entity_type='ORDER',
                entity_id=order_id,
                entity_details=f"Создан заказ №{order_number} на сумму {self.format_price(total_sum)}",
                new_values={
                    'order_number': order_number,
                    'order_date': str(order_date),
                    'delivery_date': str(delivery_date),
                    'pickup_point_id': pickup_point_id,
                    'user_id': client_id,
                    'status': status,
                    'items_count': len(items_data),
                    'total': total_sum
                }
            )

            messagebox.showinfo("Успех",
                                f"Заказ №{order_number} успешно создан!\n"
                                f"Код получения: {pickup_code}")

            # Переходим к списку заказов
            self.show_all_orders()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать заказ: {e}")

    def clear_new_order(self):
        """Очистка формы создания заказа"""
        if messagebox.askyesno("Подтверждение", "Очистить форму?"):
            self.new_order_items = []
            self.update_order_items_display()
            self.new_order_quantity.delete(0, tk.END)
            self.new_order_quantity.insert(0, "1")

    def manage_orders(self):
        self.clear_main_frame()

        title = tk.Label(self.main_frame, text="Управление заказами",
                         font=("Times New Roman", 18, "bold"), bg='#FFFFFF')
        title.pack(pady=10)

        # Статистика
        stats_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        stats_frame.pack(fill=tk.X, pady=20)

        orders = self.db.get_orders()

        stats = {
            'Всего заказов': len(orders),
            'Новые': len([o for o in orders if o['status'] == 'Новый']),
            'В обработке': len([o for o in orders if o['status'] == 'В обработке']),
            'Завершенные': len([o for o in orders if o['status'] == 'Завершен']),
            'Отмененные': len([o for o in orders if o['status'] == 'Отменен'])
        }

        for i, (key, value) in enumerate(stats.items()):
            stat_card = tk.Frame(stats_frame, bg='#F0F0F0', relief=tk.RAISED, bd=2, width=150, height=80)
            stat_card.grid(row=0, column=i, padx=10, pady=5)
            stat_card.grid_propagate(False)

            tk.Label(stat_card, text=key, bg='#F0F0F0', font=("Times New Roman", 10)).pack(pady=5)
            tk.Label(stat_card, text=str(value), bg='#F0F0F0',
                     font=("Times New Roman", 16, "bold"), fg='#2E8B57').pack()

        # Кнопки действий
        actions_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        actions_frame.pack(pady=20)

        tk.Button(actions_frame, text="Просмотреть все заказы",
                  command=self.show_all_orders,
                  bg='#00FA9A', width=20, height=2).pack(side=tk.LEFT, padx=10)

        # Добавляем кнопку создания нового заказа
        tk.Button(actions_frame, text="➕ Создать новый заказ",
                  command=self.create_new_order,  # Теперь метод существует
                  bg='#00FA9A', width=20, height=2).pack(side=tk.LEFT, padx=10)

        # Информация о последних заказах
        info_frame = tk.Frame(self.main_frame, bg='#F0F0F0', relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(info_frame, text="Последние заказы:",
                 font=("Times New Roman", 14, "bold"), bg='#F0F0F0').pack(anchor='w', padx=10, pady=10)

        # Таблица последних заказов
        recent_orders = orders[:5] if orders else []
        if recent_orders:
            for order in recent_orders:
                order_frame = tk.Frame(info_frame, bg='#FFFFFF', relief=tk.RIDGE, bd=1)
                order_frame.pack(fill=tk.X, padx=10, pady=2)

                tk.Label(order_frame,
                         text=f"{order['order_number']} - {order['full_name']} - {order['status']}",
                         bg='#FFFFFF').pack(side=tk.LEFT, padx=10, pady=5)

                view_btn = tk.Button(order_frame, text="👁️",
                                     command=lambda o=order: self.show_order_details(o),
                                     bg='#00FA9A', width=2)
                view_btn.pack(side=tk.RIGHT, padx=5)
        else:
            tk.Label(info_frame, text="Нет заказов", bg='#F0F0F0').pack(pady=20)

    def show_logs(self):
        """Показывает историю действий"""
        self.clear_main_frame()

        # Заголовок
        title = tk.Label(self.main_frame, text="Журнал действий",
                         font=("Times New Roman", 18, "bold"), bg='#FFFFFF')
        title.pack(pady=10)

        # Панель фильтрации
        filter_frame = tk.Frame(self.main_frame, bg='#FFFFFF')
        filter_frame.pack(fill=tk.X, pady=10)

        # Фильтр по дате
        date_frame = tk.Frame(filter_frame, bg='#FFFFFF')
        date_frame.pack(fill=tk.X, pady=5)

        tk.Label(date_frame, text="Дата с:", bg='#FFFFFF').pack(side=tk.LEFT, padx=5)
        self.log_date_from = tk.Entry(date_frame, width=12)
        self.log_date_from.pack(side=tk.LEFT, padx=5)
        self.log_date_from.insert(0, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))

        tk.Label(date_frame, text="по:", bg='#FFFFFF').pack(side=tk.LEFT, padx=5)
        self.log_date_to = tk.Entry(date_frame, width=12)
        self.log_date_to.pack(side=tk.LEFT, padx=5)
        self.log_date_to.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # Фильтры по типу
        filter2_frame = tk.Frame(filter_frame, bg='#FFFFFF')
        filter2_frame.pack(fill=tk.X, pady=5)

        tk.Label(filter2_frame, text="Действие:", bg='#FFFFFF').pack(side=tk.LEFT, padx=5)
        action_types = ["Все действия", "CREATE", "UPDATE", "DELETE"]
        self.log_action_var = tk.StringVar(value="Все действия")
        action_combo = ttk.Combobox(filter2_frame, textvariable=self.log_action_var,
                                    values=action_types, width=15, state='readonly')
        action_combo.pack(side=tk.LEFT, padx=5)

        tk.Label(filter2_frame, text="Сущность:", bg='#FFFFFF').pack(side=tk.LEFT, padx=5)
        entity_types = ["Все сущности", "PRODUCT", "ORDER"]
        self.log_entity_var = tk.StringVar(value="Все сущности")
        entity_combo = ttk.Combobox(filter2_frame, textvariable=self.log_entity_var,
                                    values=entity_types, width=15, state='readonly')
        entity_combo.pack(side=tk.LEFT, padx=5)

        # Поиск
        tk.Label(filter2_frame, text="Поиск:", bg='#FFFFFF').pack(side=tk.LEFT, padx=5)
        self.log_search = tk.Entry(filter2_frame, width=30)
        self.log_search.pack(side=tk.LEFT, padx=5)

        # Кнопка применения фильтров
        tk.Button(filter2_frame, text="Применить", command=self.load_logs,
                  bg='#00FA9A', width=10).pack(side=tk.LEFT, padx=20)

        # Кнопка экспорта
        tk.Button(filter2_frame, text="📥 Экспорт", command=self.export_logs,
                  bg='#7FFF00', width=10).pack(side=tk.LEFT)

        # Контейнер для таблицы логов
        table_frame = tk.Frame(self.main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Создаем таблицу
        columns = ("Дата", "Пользователь", "Действие", "Сущность", "ID", "Детали")
        self.logs_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        # Настройка колонок
        col_widths = [150, 200, 80, 80, 50, 400]
        for col, width in zip(columns, col_widths):
            self.logs_tree.heading(col, text=col)
            self.logs_tree.column(col, width=width, minwidth=width)

        self.logs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Скроллбар
        scrollbar = tk.Scrollbar(table_frame, orient="vertical", command=self.logs_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.logs_tree.configure(yscrollcommand=scrollbar.set)

        # Привязка двойного клика для просмотра деталей
        self.logs_tree.bind('<Double-1>', self.show_log_details)

        # Загружаем логи
        self.load_logs()

        # Статистика
        self.load_log_stats()

    def load_logs(self):
        """Загрузка логов с фильтрацией"""
        # Очищаем текущий список
        for item in self.logs_tree.get_children():
            self.logs_tree.delete(item)

        # Получаем фильтры
        filters = {
            'action_type': self.log_action_var.get(),
            'entity_type': self.log_entity_var.get(),
            'date_from': self.log_date_from.get(),
            'date_to': self.log_date_to.get(),
            'search': self.log_search.get()
        }

        logs = self.db.get_action_logs(filters)

        if not logs:
            self.logs_tree.insert("", "end", values=("", "", "Нет данных", "", "", ""))
            return

        # Заполняем таблицу
        for log in logs:
            # Форматируем дату
            date_str = log['action_date'].strftime('%d.%m.%Y %H:%M') if log['action_date'] else ""

            # Определяем цвет для действия
            tag = None
            if log['action_type'] == 'CREATE':
                tag = 'create'
            elif log['action_type'] == 'UPDATE':
                tag = 'update'
            elif log['action_type'] == 'DELETE':
                tag = 'delete'

            item_id = self.logs_tree.insert("", "end", values=(
                date_str,
                log['user_name'],
                log['action_type'],
                log['entity_type'],
                log['entity_id'] or "",
                log['entity_details'] or ""
            ))

            if tag:
                self.logs_tree.item(item_id, tags=(tag,))

        # Настройка цветов
        self.logs_tree.tag_configure('create', background='#90EE90')  # светло-зеленый
        self.logs_tree.tag_configure('update', background='#FFD700')  # золотой
        self.logs_tree.tag_configure('delete', background='#FFB6C1')  # светло-розовый

    def load_log_stats(self):
        """Загрузка статистики по логам"""
        # Статистика внизу страницы
        stats_frame = tk.Frame(self.main_frame, bg='#F0F0F0', relief=tk.RAISED, bd=2)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)

        # Получаем общее количество записей
        total = len(self.logs_tree.get_children())

        # Считаем по типам
        cursor = self.db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN action_type = 'CREATE' THEN 1 ELSE 0 END) as creates,
                SUM(CASE WHEN action_type = 'UPDATE' THEN 1 ELSE 0 END) as updates,
                SUM(CASE WHEN action_type = 'DELETE' THEN 1 ELSE 0 END) as deletes
            FROM action_logs
            WHERE DATE(action_date) >= %s AND DATE(action_date) <= %s
        """, (self.log_date_from.get(), self.log_date_to.get()))

        stats = cursor.fetchone()

        stats_text = f"Всего записей: {stats['total']} | Создано: {stats['creates']} | Изменено: {stats['updates']} | Удалено: {stats['deletes']}"
        tk.Label(stats_frame, text=stats_text, bg='#F0F0F0',
                 font=("Times New Roman", 11, "bold")).pack(pady=5)

    def show_log_details(self, event):
        """Показывает детальную информацию о логе"""
        selection = self.logs_tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.logs_tree.item(item, "values")

        # Получаем полную запись из БД
        cursor = self.db.connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM action_logs WHERE DATE(action_date) = %s AND user_name = %s ORDER BY action_date DESC LIMIT 1",
            (values[0][:10], values[1]))  # Упрощенно, лучше передавать ID
        log = cursor.fetchone()

        if not log:
            return

        # Создаем окно с деталями
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Детали действия - {log['action_type']}")
        details_window.geometry("600x500")
        details_window.configure(bg='#FFFFFF')

        # Центрируем окно
        details_window.update_idletasks()
        width = details_window.winfo_width()
        height = details_window.winfo_height()
        x = (details_window.winfo_screenwidth() // 2) - (width // 2)
        y = (details_window.winfo_screenheight() // 2) - (height // 2)
        details_window.geometry(f'{width}x{height}+{x}+{y}')

        # Заголовок
        tk.Label(details_window, text=f"Детали действия: {log['action_type']}",
                 font=("Times New Roman", 16, "bold"), bg='#FFFFFF').pack(pady=10)

        # Основная информация
        info_frame = tk.Frame(details_window, bg='#F0F0F0', relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        info_text = f"""
        Дата и время: {log['action_date'].strftime('%d.%m.%Y %H:%M:%S')}
        Пользователь: {log['user_name']} (ID: {log['user_id']})
        Тип действия: {log['action_type']}
        Тип сущности: {log['entity_type']}
        ID сущности: {log['entity_id'] or 'Не указан'}
        Детали: {log['entity_details'] or 'Нет'}
        """

        tk.Label(info_frame, text=info_text, bg='#F0F0F0', justify=tk.LEFT,
                 font=("Times New Roman", 11)).pack(padx=10, pady=10)

        # Старые значения
        if log['old_values']:
            old_frame = tk.Frame(details_window, bg='#FFE4E1', relief=tk.RAISED, bd=2)
            old_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

            tk.Label(old_frame, text="Старые значения:", bg='#FFE4E1',
                     font=("Times New Roman", 12, "bold")).pack(anchor='w', padx=10, pady=5)

            import json
            old_values = json.loads(log['old_values'])
            old_text = tk.Text(old_frame, height=8, width=70, bg='#FFE4E1')
            old_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

            for key, value in old_values.items():
                old_text.insert(tk.END, f"{key}: {value}\n")
            old_text.config(state=tk.DISABLED)

        # Новые значения
        if log['new_values']:
            new_frame = tk.Frame(details_window, bg='#E0FFE0', relief=tk.RAISED, bd=2)
            new_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

            tk.Label(new_frame, text="Новые значения:", bg='#E0FFE0',
                     font=("Times New Roman", 12, "bold")).pack(anchor='w', padx=10, pady=5)

            import json
            new_values = json.loads(log['new_values'])
            new_text = tk.Text(new_frame, height=8, width=70, bg='#E0FFE0')
            new_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

            for key, value in new_values.items():
                new_text.insert(tk.END, f"{key}: {value}\n")
            new_text.config(state=tk.DISABLED)

        # Кнопка закрытия
        tk.Button(details_window, text="Закрыть", command=details_window.destroy,
                  bg='#7FFF00', width=15).pack(pady=20)

    def export_logs(self):
        """Экспорт логов в CSV"""
        from tkinter import filedialog
        import csv

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Сохранить логи как"
        )

        if not filename:
            return

        try:
            # Получаем текущие фильтры
            filters = {
                'action_type': self.log_action_var.get(),
                'entity_type': self.log_entity_var.get(),
                'date_from': self.log_date_from.get(),
                'date_to': self.log_date_to.get(),
                'search': self.log_search.get()
            }

            logs = self.db.get_action_logs(filters)

            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['Дата', 'Пользователь', 'Действие', 'Сущность', 'ID', 'Детали']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')

                writer.writeheader()
                for log in logs:
                    writer.writerow({
                        'Дата': log['action_date'].strftime('%d.%m.%Y %H:%M:%S'),
                        'Пользователь': log['user_name'],
                        'Действие': log['action_type'],
                        'Сущность': log['entity_type'],
                        'ID': log['entity_id'] or '',
                        'Детали': log['entity_details'] or ''
                    })

            messagebox.showinfo("Успех", f"Логи экспортированы в файл:\n{filename}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать логи: {e}")
    def logout(self):
        self.root.destroy()
        LoginWindow(self.db).run()

    def run(self):
        self.root.mainloop()




if __name__ == "__main__":
    # Создаем папку для изображений, если её нет
    if not os.path.exists("images"):
        os.makedirs("images")
        print("Создана папка images. Поместите туда изображения товаров.")

    # Проверяем наличие файла-заглушки
    if not os.path.exists("picture.png"):
        print("Предупреждение: файл picture.png не найден. Будет использован текстовый плейсхолдер.")

    try:
        # Подключаемся к базе данных
        db = Database()

        # Запускаем приложение
        app = LoginWindow(db)
        app.run()
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Не удалось запустить приложение: {e}")