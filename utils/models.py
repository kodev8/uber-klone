from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy_utils import PhoneNumberType
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
# from datetime import datetime
from utils.extensions import db
from utils.config import ADMIN_PASSWORD

# USERS
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = mapped_column(db.Integer, primary_key=True, autoincrement=True)
    fname = mapped_column(db.String(50), nullable=False)
    lname = mapped_column(db.String(50), nullable=False)
    email = mapped_column(db.String(255), unique =True, nullable=False)
    password = mapped_column(db.String(255), nullable=True)
    user_since = mapped_column(db.DateTime(timezone=True), nullable=False,server_default=func.now())
    profile_pic = mapped_column(db.String(255), nullable=True)
    phone = mapped_column(PhoneNumberType, nullable=True)

    # relationships
    roles = relationship('Role', secondary='user_roles')

    # _user_locale = None

    def __repr__(self):
        return f"ID: {self.id}, NAME: {self.display_name()} ROLES: {self.roles}"


    # @property
    # def user_locale(self):
    #     return self._user_locale if hasattr(self, '_user_locale') else 'en'

    # @user_locale.setter
    # def user_locale(self, locale):
    #     if locale not in Config.LANGUAGES:
    #         self._user_locale = locale
    #     else:
    #         self._user_locale = 'en'


    @staticmethod
    def remove_all():
        """ remove all users from db """
        db.session.query(User).delete()
        db.session.commit()

        
    @staticmethod
    def get_by_id(user_id : int):
        """ get user by id
            :param user_id: user id
        """
        return db.session.scalars(db.select(User).filter_by(id=user_id)).first()
    
    @staticmethod
    def get_by_email(email):
        """ get user by email
            :param email: user email address
        """
        query = db.select(User).filter_by(email=email)
        return  db.session.scalars(query).first()
    
    @staticmethod
    def add_user(user):
        """ add user to db 
            :param user: user object
        """
        assert isinstance(user, User), "User must be an instance of User class"
        db.session.add(user)
        db.session.commit()

    @staticmethod
    def create_admin():
        """ create admin user if not exists """
        admin = User.get_by_id(0)
        if not admin:
            admin = User(id=0, fname='admin', lname='admin', email='admin@kuber.co')
            admin.set_password(ADMIN_PASSWORD)
            Role._init_roles()
            admin.roles.append(Role.get_by_name('admin'))
            User.add_user(admin)

    def public_profile(self):
        """ return public profile of user """
        return {
            'fname': self.fname,
            'lname': self.lname,
            'email': self.email,
            'profile_pic': self.profile_pic,
            'phone': self.phone
        }

    def display_name(self):
        """ return user's full name """
        return self.fname + ' ' + self.lname
    
    def build_path(self, folder:str='', filename:str=''):
        """ build path for user's profile picture 
            :param folder: folder name
            :param filename: filename
        """
        return f'user_{self.id}/{folder}/{filename}'
    
    def update_email(self, email: str):
        """ update user's email address
            :param email: new email address 
        """
        self.email = email
        db.session.commit()
    
    def update_name(self, fname: str, lname: str):
        """ update user's name
            :param fname: first name
            :param lname: last name
        """
        self.fname = fname
        self.lname = lname
        db.session.commit()
    
    def update_phone(self, phone):  #phone number type
        """ update user's phone number
            :param phone: phone number
        """
        self.phone = phone
        db.session.commit()

    def update_profile_pic(self, isset : bool):
        """ update user's profile picture
            :param isset: is profile picture set
        """
        self.profile_pic = None if not isset else 'is_set'
        db.session.commit()

    def check_password(self, password : str):
        """ check if password is correct
            :param password: password to check
        """
        return check_password_hash(self.password, password)
    
    def set_password(self, password : str):
        """ set user's password
            :param password: password to set
        """
        self.password = generate_password_hash(password)
        db.session.commit()

    def has_role(self, role_name : str):
        """ check if user has a role
            :param role_name: role name
        """
        return any(role.name == role_name for role in self.roles)

    def add_role(self, role_name : str):
        """ add role to user
            :param role_name: role name
        """
        role = Role.get_by_name(role_name)
        if role and role not in self.roles:
            self.roles.append(role)
            db.session.commit()
        
class Role(db.Model):
    __tablename__ = 'roles'
    id = mapped_column(db.Integer(), primary_key=True)
    name = mapped_column(db.String(50), unique=True)

    def __repr__(self):
        return f'<Role {self.name}>'
    
    @staticmethod
    def _init_roles():
        """ initialize roles """
        roles = ['admin', 'driver', 'rider']
        for role in roles:
            if not Role.get_by_name(role):
                Role.__add_role(role)
    
    @staticmethod
    def get_by_name(name):
        """ get role by name  
            :param name: role name
        """

        query = db.select(Role).filter_by(name=name)
        return db.session.scalars(query).first()

    @staticmethod
    def __add_role(name):
        """ private method to add role to db
            :param name: role name
        """
        role = Role(name=name)
        db.session.add(role)
        db.session.commit()

class UserRoles(db.Model):
    """ user roles table 
        Intermediate table for many-to-many relationship between users and roles
    """
    __tablename__ = 'user_roles'
    id = mapped_column(db.Integer(), primary_key=True, autoincrement=True)
    user_id = mapped_column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = mapped_column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

    @staticmethod
    def remove_all():
        """ remove all user roles from db """
        db.session.query(UserRoles).delete()
        db.session.commit()
        
# Used in prev version
class TokenBlocklist(db.Model):
    """ token blocklist table
        Used to store revoked/valid jwt tokens
    """
    id = mapped_column(db.Integer, primary_key=True)
    jti = mapped_column(db.String(36), nullable=False, index=True)
    type = mapped_column(db.String(16), nullable=False)
    user_id = mapped_column(db.ForeignKey('users.id'), nullable=False)
    revoked = mapped_column(db.Boolean, nullable=False, default=False)
    created_at = mapped_column(db.DateTime(timezone=True),server_default=func.now(),nullable=False)

    def __repr__(self):
        return f'<TokenBlocklist {self.jti}, user={self.user_id}, revoked={self.revoked}>'

    @staticmethod
    def add_token(token):
        assert isinstance(token, TokenBlocklist), "Token must be an instance of TokenBlocklist class"
        db.session.add(token)
        db.session.commit()

    @staticmethod
    def test_token_revoked(token_jti):
        print('testing token', token_jti)
        token = db.session.query(TokenBlocklist).filter_by(jti=token_jti, revoked=True).first()
        print('token found', token)
        return token is not None

    @staticmethod
    def revoke_token(user_id, token_jti, token_type):
        token = db.session.query(TokenBlocklist).filter_by(jti=token_jti).first()
        if not token:
            print('token not found')
            return
        print('token found', token_jti)
        token.revoked = True
        db.session.commit()

    @staticmethod
    def revoke_all_user_tokens(user_id):
        db.session.query(TokenBlocklist).filter_by(user_id=user_id).update({'revoked': True})
        db.session.commit()
        
    