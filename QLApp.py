from flask import Flask, jsonify
from flask_graphql import GraphQLView
from flask_cors import CORS
import graphene
from graphene import Mutation, ObjectType, String, ID, Field, InputObjectType, List
from flask_pymongo import PyMongo
from bson import ObjectId
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from flask import render_template

app = Flask(__name__)
CORS(app)

app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_app'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
jwt = JWTManager(app)
mongo = PyMongo(app)

class Todo(graphene.ObjectType):
    id = graphene.ID()
    title = graphene.String()
    description = graphene.String()
    time = graphene.String()
    image = graphene.String()

class TodoInput(graphene.InputObjectType):
    title = graphene.String(required=True)
    description = graphene.String(required=True)
    time = graphene.String(required=True)
    image = graphene.String()

class Query(ObjectType):
    todos = graphene.List(Todo, description="List all To-Dos")

    @jwt_required()
    def resolve_todos(root, info):
        user_id = get_jwt_identity()

        # Fetch todos from MongoDB based on user_id
        todos = mongo.db.todos.find({"user_id": user_id})

        # Convert MongoDB documents to GraphQL Todo objects
        return [Todo(
            id=str(todo['_id']),
            title=todo['title'],
            description=todo['description'],
            time=todo['time'],
            image=todo['image']
        ) for todo in todos]

class CreateTodoMutation(Mutation):
    class Arguments:
        todo = TodoInput(required=True)

    todo = Field(lambda: Todo)

    @jwt_required()
    def mutate(self, info, todo):
        user_id = get_jwt_identity()

        # Create a new todo document in MongoDB
        new_todo = {
            "user_id": user_id,
            "title": todo.title,
            "description": todo.description,
            "time": todo.time,
            "image": todo.image,
        }
        result = mongo.db.todos.insert_one(new_todo)

        # Fetch the created todo from MongoDB
        created_todo = mongo.db.todos.find_one({"_id": result.inserted_id})

        return CreateTodoMutation(
            todo=Todo(
                id=str(created_todo['_id']),
                title=created_todo['title'],
                description=created_todo['description'],
                time=created_todo['time'],
                image=created_todo['image']
            )
        )

class DeleteTodoMutation(Mutation):
    class Arguments:
        id = ID(required=True)

    success = String()

    @jwt_required()
    def mutate(self, info, id):
        user_id = get_jwt_identity()

        # Delete the todo from MongoDB if it belongs to the authenticated user
        result = mongo.db.todos.delete_one({"_id": ObjectId(id), "user_id": user_id})

        if result.deleted_count > 0:
            return DeleteTodoMutation(success=f"Todo {id} deleted successfully.")
        else:
            return DeleteTodoMutation(success=f"Todo {id} not found or unauthorized.")

class Mutation(ObjectType):
    create_todo = CreateTodoMutation.Field()
    delete_todo = DeleteTodoMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)

app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=True),
)

if __name__ == "__main__":
    app.run(debug=True)
