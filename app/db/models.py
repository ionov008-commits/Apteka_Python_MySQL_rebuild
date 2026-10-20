import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Numeric
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "user"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    Username = Column(String(100), nullable=True)  # Регистр сохранен как в дампе
    Email = Column(String(255), nullable=True)     # Регистр сохранен как в дампе

    customer = relationship("Customer", back_populates="user", uselist=False, cascade="all, delete")
    pharmacy = relationship("Pharmacy", back_populates="user", uselist=False, cascade="all, delete")
    pharmacist = relationship("Pharmacist", back_populates="user", uselist=False, cascade="all, delete")


class Customer(Base):
    __tablename__ = "customer"

    customer_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), unique=True, nullable=False)
    default_address = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    user = relationship("User", back_populates="customer")
    orders = relationship("CustomerOrder", back_populates="customer", cascade="all, delete")


class Pharmacy(Base):
    __tablename__ = "pharmacy"

    pharmacy_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(50), nullable=True)
    director_name = Column(String(255), nullable=True)
    working_hours = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    user = relationship("User", back_populates="pharmacy")
    stocks = relationship("PharmacyStock", back_populates="pharmacy", cascade="all, delete")
    pharmacists = relationship("Pharmacist", back_populates="pharmacy", cascade="all, delete")


class Pharmacist(Base):
    __tablename__ = "pharmacists"

    pharmacist_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    pharmacy_id = Column(Integer, ForeignKey("pharmacy.pharmacy_id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    working_hours = Column(String(255), nullable=True)

    user = relationship("User", back_populates="pharmacist")
    pharmacy = relationship("Pharmacy", back_populates="pharmacists")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    active_substance = Column(Text, nullable=True)
    image = Column(Text, nullable=True)
    form = Column(String(100), nullable=True)
    dosage = Column(String(100), nullable=True)
    prescription_required = Column(Integer, default=0)
    description = Column(Text, nullable=True)

    stocks = relationship("PharmacyStock", back_populates="product", cascade="all, delete")

    @property
    def display_image(self) -> str:
        if self.image:
            return self.image
        return f"{self.product_id}.png"


class PharmacyStock(Base):
    __tablename__ = "pharmacy_stock"

    stock_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacy.pharmacy_id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=0)
    price = Column(Numeric(10, 2), nullable=True)

    pharmacy = relationship("Pharmacy", back_populates="stocks")
    product = relationship("Product", back_populates="stocks")
    order_items = relationship("OrderItem", back_populates="stock", cascade="all, delete")


class CustomerOrder(Base):
    __tablename__ = "customer_orders"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customer.customer_id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="новый")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    total_cost = Column(Numeric(10, 2), nullable=True)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("customer_orders.order_id", ondelete="CASCADE"), nullable=False)
    stock_id = Column(Integer, ForeignKey("pharmacy_stock.stock_id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String(50), default="Pending")

    order = relationship("CustomerOrder", back_populates="items")
    stock = relationship("PharmacyStock", back_populates="order_items")