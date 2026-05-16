from datetime import datetime, timezone
from typing import List, Optional
from flask_login import UserMixin
from sqlalchemy import Index, Table, Boolean, CheckConstraint, Column, String, Integer, ForeignKey, Text, DateTime, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from flaskr.extensions import db_SQLAlchemy

# Helper to get the current UTC time with timezone info
def utc_now():
    return datetime.now(timezone.utc)

# USERS and ROLES
# Association table for User <-> Role
user_role = Table(
    "user_role",
    db_SQLAlchemy.Model.metadata,
    Column(
        "user_id", 
        Integer, 
        ForeignKey("user.id", ondelete="CASCADE"), 
        primary_key=True
    ),
    Column(
        "role_id", 
        Integer, 
        ForeignKey("role.id", ondelete="CASCADE"), 
        primary_key=True
    ),
)

class Role(db_SQLAlchemy.Model):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

class User(db_SQLAlchemy.Model, UserMixin):
    __tablename__ = "user"

    # id is automatically handled as autoincrement by SQLAlchemy for Integer primary keys
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Flask-Login usually manages these as properties, 
    # but since you defined them in SQL, we map them here:
    #is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    #is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship to Roles
    roles: Mapped[list["Role"]] = relationship("Role", secondary=user_role)
    
    # Content Created by User
    games: Mapped[List["Game"]] = relationship("Game", back_populates="author")
    elements: Mapped[List["Element"]] = relationship("Element", back_populates="author")
    tags_created: Mapped[List["Tag"]] = relationship("Tag", back_populates="author")
    
    # Game and Element Metadata
    game_links: Mapped[List["GameLink"]] = relationship("GameLink", back_populates="author")
    game_tags: Mapped[List["GameTag"]] = relationship("GameTag", back_populates="author")
    game_elements: Mapped[List["GameAndElement"]] = relationship("GameAndElement", back_populates="author")
    
    # Interactions
    votes: Mapped[List["Vote"]] = relationship("Vote", back_populates="user")
    feedbacks: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="author")

    # Deep Metadata (Elements)
    element_common_variants: Mapped[List["ElementCommonVariant"]] = relationship("ElementCommonVariant", back_populates="author")
    element_links: Mapped[List["ElementLink"]] = relationship("ElementLink", back_populates="author")
    element_tags: Mapped[List["ElementTag"]] = relationship("ElementTag", back_populates="author")
    element_values: Mapped[List["ElementValue"]] = relationship("ElementValue", back_populates="author")

    # Variants and Compositions
    game_element_variants: Mapped[List["GameElementVariant"]] = relationship("GameElementVariant", back_populates="author")
    game_element_links: Mapped[List["GameElementLink"]] = relationship("GameElementLink", back_populates="author")
    game_element_tags: Mapped[List["GameElementTag"]] = relationship("GameElementTag", back_populates="author")
    compositions: Mapped[List["CompositionOfElement"]] = relationship("CompositionOfElement", back_populates="author")
    
    # Likes
    game_element_variant_likes: Mapped[list["GameElementVariantLike"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    def get_id(self):
        """Returns the user ID as a string, required by Flask-Login."""
        return str(self.id)
    
    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)
# END USERS and ROLES

# ELEMENTS
class Tag(db_SQLAlchemy.Model):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    
    # Relationships
    author: Mapped["User"] = relationship("User", back_populates="tags_created")
    element_tags: Mapped[List["ElementTag"]] = relationship("ElementTag", back_populates="tag")

class Element(db_SQLAlchemy.Model):
    __tablename__ = "element"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    status: Mapped[str] = mapped_column(
        Text, 
        CheckConstraint("status IN ('private', 'pending_review', 'public')"), 
        default='private'
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(Text) # Storing tags as a string/list

    # Foreign Key for self-referential parent
    # Note: Your SQL had REFERENCES element(id) but didn't define parent_id in the columns list
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("element.id", ondelete="SET NULL"))

    # Relationships
    author: Mapped["User"] = relationship("User", back_populates="elements")
    
    # Self-referential relationship
    parent: Mapped[Optional["Element"]] = relationship("Element", remote_side=[id], backref="children")
    
    links: Mapped[List["ElementLink"]] = relationship("ElementLink", back_populates="element")
    common_variants: Mapped[List["ElementCommonVariant"]] = relationship("ElementCommonVariant", back_populates="element")
    element_tags: Mapped[List["ElementTag"]] = relationship("ElementTag", back_populates="element")
    element_values: Mapped[List["ElementValue"]] = relationship("ElementValue", back_populates="element")

class ElementLink(db_SQLAlchemy.Model):
    __tablename__ = "element_link"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    element_id: Mapped[int] = mapped_column(ForeignKey("element.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    
    element: Mapped["Element"] = relationship("Element", back_populates="links")
    author: Mapped["User"] = relationship("User", back_populates="element_links")

class ElementTag(db_SQLAlchemy.Model):
    __tablename__ = "element_tag"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    element_id: Mapped[int] = mapped_column(ForeignKey("element.id", ondelete="CASCADE"))
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    element: Mapped["Element"] = relationship("Element", back_populates="element_tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="element_tags")
    author: Mapped["User"] = relationship("User", back_populates="element_tags")

class ElementValue(db_SQLAlchemy.Model):
    __tablename__ = "element_value"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[str] = mapped_column(
        Text, 
        CheckConstraint("status IN ('private', 'pending_review', 'public')"), 
        default='private'
    )

    element_id: Mapped[int] = mapped_column(ForeignKey("element.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    
    element: Mapped["Element"] = relationship("Element", back_populates="element_values")
    author: Mapped["User"] = relationship("User", back_populates="element_values")

class CompositionOfElement(db_SQLAlchemy.Model):
    __tablename__ = "composition_of_element"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    element_id: Mapped[Optional[int]] = mapped_column(ForeignKey("element.id", ondelete="CASCADE"))
    subelement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("element.id", ondelete="RESTRICT"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    # Relationships to identify which element is which in the composition
    main_element: Mapped["Element"] = relationship("Element", foreign_keys=[element_id])
    sub_element: Mapped["Element"] = relationship("Element", foreign_keys=[subelement_id])
    author: Mapped["User"] = relationship("User", back_populates="compositions")

class ElementCommonVariant(db_SQLAlchemy.Model):
    __tablename__ = "element_common_variant"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    element_id: Mapped[int] = mapped_column(ForeignKey("element.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    
    element: Mapped["Element"] = relationship("Element", back_populates="common_variants")
    author: Mapped["User"] = relationship("User", back_populates="element_common_variants")

# END ELEMENTS

# GAMES
class Game(db_SQLAlchemy.Model):
    __tablename__ = "game"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    
    # Use datetime.utcnow as a callable for the default value
    created: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow
    )
    
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Implementing the CHECK constraint for status
    status: Mapped[str] = mapped_column(
        String(20), 
        CheckConstraint("status IN ('private', 'pending_review', 'public')"),
        nullable=False, 
        default='private'
    )

    # Optional: Relationship back to the User model
    # This allows you to do `game.author.username` easily
    author: Mapped["User"] = relationship("User", back_populates="games")

    def __repr__(self) -> str:
        return f"<Game {self.title!r}>"

class GameLink(db_SQLAlchemy.Model):
    __tablename__ = "game_link"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    
    author: Mapped["User"] = relationship("User", back_populates="game_links")

class GameTag(db_SQLAlchemy.Model):
    __tablename__ = "game_tag"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    
    author: Mapped["User"] = relationship("User", back_populates="game_tags")
# END GAMES

# GAME ELEMENTS
class GameAndElement(db_SQLAlchemy.Model):
    __tablename__ = "game_and_element"
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    link: Mapped[Optional[str]] = mapped_column(Text)
    weight: Mapped[int] = mapped_column(default=0)
    element_order: Mapped[int] = mapped_column(default=0)
    #created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    #is_reviewed_befor_publication = Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    
    game_id: Mapped[Optional[int]] = mapped_column(ForeignKey("game.id", ondelete="CASCADE"))
    type_of_id: Mapped[str] = mapped_column(
        Text, 
        CheckConstraint("type_of_id IN ('element', 'game_element')"), 
        default='element'
    )
    element_id: Mapped[Optional[int]] = mapped_column(ForeignKey("element.id", ondelete="RESTRICT"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    # Self-referential Foreign Keys
    game_element_id: Mapped[Optional[int]] = mapped_column(ForeignKey("game_and_element.id", ondelete="CASCADE"))
    parent_element_id: Mapped[Optional[int]] = mapped_column(ForeignKey("game_and_element.id", ondelete="CASCADE"))
    previous_game_element_id: Mapped[Optional[int]] = mapped_column(ForeignKey("game_and_element.id", ondelete="SET NULL"))

    # Relationships
    parent: Mapped[Optional["GameAndElement"]] = relationship(
        "GameAndElement", remote_side=[id], foreign_keys=[parent_element_id]
    )
    author: Mapped["User"] = relationship("User", back_populates="game_elements")
    
class GameElementTag(db_SQLAlchemy.Model):
    __tablename__ = "game_element_tag"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    game_element_id: Mapped[int] = mapped_column(ForeignKey("game_and_element.id", ondelete="CASCADE"))
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id", ondelete="SET NULL"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    
    author: Mapped["User"] = relationship("User", back_populates="game_element_tags")

class GameElementLink(db_SQLAlchemy.Model):
    __tablename__ = "game_element_link"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    link: Mapped[str] = mapped_column(Text, default='')
    title: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    game_element_id: Mapped[int] = mapped_column(ForeignKey("game_and_element.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))

    author: Mapped["User"] = relationship("User", back_populates="game_element_links")

class GameElementVariant(db_SQLAlchemy.Model):
    __tablename__ = "game_element_variant"
    id: Mapped[int] = mapped_column(primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    
    target_type: Mapped[str] = mapped_column(
        Text, CheckConstraint("target_type IN ('game', 'game_and_element')")
    )
    #status: Mapped[str] = mapped_column(
    #    Text, 
    #    CheckConstraint("status IN ('private', 'pending_review', 'public')"), 
    #    default='private'
    #)
    admin_feedback: Mapped[str | None] = mapped_column(String(500))
    
    status_name: Mapped[str] = mapped_column(
        ForeignKey("variant_status.name"),
        nullable=False,
        server_default=text("'private'")
    )
    game_id: Mapped[Optional[int]] = mapped_column(ForeignKey("game.id", ondelete="CASCADE"))
    game_element_id: Mapped[Optional[int]] = mapped_column(ForeignKey("game_and_element.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    
    author: Mapped["User"] = relationship("User", back_populates="game_element_variants")
    statuses: Mapped["VariantStatus"] = relationship(back_populates="statuses")
    likes: Mapped[list["GameElementVariantLike"]] = relationship(back_populates="variant", cascade="all, delete-orphan")

# END GAME ELEMENTS

# VOTES and FEEDBACK    
class Vote(db_SQLAlchemy.Model):
    __tablename__ = "vote"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    target_type: Mapped[str] = mapped_column(
        String(20), 
        CheckConstraint("target_type IN ('game', 'game_and_element')"),
        nullable=False
    )
    
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    vote_value: Mapped[int] = mapped_column(
        Integer, 
        CheckConstraint("vote_value IN (1, -1)"),
        nullable=False
    )
    
    # We set timezone=True in the DateTime type
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )
    
    # onupdate also needs the timezone-aware function
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now, 
        onupdate=utc_now
    )

    user: Mapped["User"] = relationship("User", back_populates="votes")

    __table_args__ = (
        # Unique constraint (also acts as an index)
        UniqueConstraint("user_id", "target_type", "target_id", name="uix_user_target"),
        
        # Explicit Index for target lookups
        Index("idx_vote_target", "target_type", "target_id"),
        
        # Explicit Index for user lookups
        Index("idx_vote_user", "user_id"),
    )

class Feedback(db_SQLAlchemy.Model):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # ON DELETE SET NULL mirrors your SQL foreign key constraint
    author_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    service_name: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Boolean mapping for your is_positive/is_negative flags
    is_positive: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    is_negative: Mapped[Optional[bool]] = mapped_column(Boolean, default=None)
    
    version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timezone-aware timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now
    )

    # Relationship back to the User model
    author: Mapped[Optional["User"]] = relationship("User", back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<Feedback from User {self.author_id} for {self.service_name}>"
# END VOTES and FEEDBACK

# STATUSES
class VariantStatus(db_SQLAlchemy.Model):
    __tablename__ = "variant_status"

    # Use a string as the primary key so that the main table stores human-readable values ('public', 'archived') instead of just IDs.
    name: Mapped[str] = mapped_column(String(30), primary_key=True)
    description: Mapped[str | None] = mapped_column(String(200))

    # Reverse relationship (optional, for ease of search)
    statuses: Mapped[List["GameElementVariant"]] = relationship(back_populates="statuses")

    def __repr__(self) -> str:
        return f"VariantStatus(name={self.name!r})"
# END STATUSES

# LIKES
class GameElementVariantLike(db_SQLAlchemy.Model):
    __tablename__ = "game_element_variant_like"

    # 1. Composite Primary Key or Single ID
    # Using a dedicated ID is often easier for modern ORMs
    id: Mapped[int] = mapped_column(primary_key=True)

    # 2. Foreign Keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), 
        nullable=False
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("game_element_variant.id", ondelete="CASCADE"), 
        nullable=False
    )

    # 3. Metadata
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    # 4. Relationships (Optional, but very helpful)
    # Allows you to do: variant.likes or user.liked_variants
    user: Mapped["User"] = relationship(back_populates="game_element_variant_likes")
    variant: Mapped["GameElementVariant"] = relationship(back_populates="likes")

    # 5. Constraints
    # Crucial: Prevent a user from liking the same variant twice!
    __table_args__ = (
        UniqueConstraint("user_id", "variant_id", name="uix_user_variant_like"),
    )
# END LIKES