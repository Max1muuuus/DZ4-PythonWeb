from app import app
from models import db, Category, Dish

DATA = {
    ("Піца", "pizza"): [
        ("Margherita", "Томатний соус, моцарела, базилік", 189, "🍕"),
        ("Quattro Formaggi", "Моцарела, горгонзола, пармезан, фонтіна", 239, "🧀"),
        ("Diavola", "Гостра салямі, моцарела, томати", 229, "🌶️"),
    ],
    ("Паста", "pasta"): [
        ("Carbonara", "Спагеті, гуанчіале, жовток, пекоріно", 219, "🍝"),
        ("Bolognese", "Тальятелле, м'ясний рагу, пармезан", 209, "🍝"),
        ("Aglio e Olio", "Спагеті, часник, оливкова олія, чилі", 169, "🧄"),
    ],
    ("Десерти", "desserts"): [
        ("Tiramisu", "Савоярді, маскарпоне, еспресо, какао", 129, "🍰"),
        ("Panna Cotta", "Вершковий десерт із ягідним соусом", 119, "🍮"),
    ],
    ("Напої", "drinks"): [
        ("Espresso", "Класичний італійський еспресо", 49, "☕"),
        ("Limonata", "Домашній лимонад з м'ятою", 69, "🍋"),
    ],
}


def seed():
    with app.app_context():
        if Category.query.count() > 0:
            print("База вже заповнена, пропускаю.")
            return
        for (name, slug), dishes in DATA.items():
            category = Category(name=name, slug=slug)
            for dname, desc, price, emoji in dishes:
                category.dishes.append(Dish(name=dname, description=desc, price=price, emoji=emoji))
            db.session.add(category)
        db.session.commit()
        print(f"Додано категорій: {Category.query.count()}, страв: {Dish.query.count()}")


if __name__ == "__main__":
    seed()
