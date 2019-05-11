# py2store
Interfacing with stored data through python.

Listing, reading, writing, and deleting data from/in a structured data source/target, 
through a common interface, as agnostic as possible of the physical particularities. 

It would be tempting to coin py2store as ya(p)orm (yet another (python) object-relational mapping), 
but that would be wrong. The intent of py2store is not to map objects to db entries, 
but rather to offer a consistent interface for basic storage operations. 
In that sense, py2store is more akin to an implementation of the data access object (DAO) pattern. 
Of course, the difference between ORM and DAO can be blurry, so all this should be taken with a grain of salt.

Advantages and disadvantages such abstractions are easy to search and find.

Most data interaction mechanisms can be satisfied by a subset of the collections.abc interfaces.
For example, one can use python's collections.Mapping interface for any key-value storage, making the data access 
object have the look and feel of a dict, instead of using other popular method name choices such for 
such as read/write, load/dump, etc. 
One of the dangers there is that, since the DAO looks and acts like a dict (but is not) a user might underestimate 
the running-costs of some operations.


# Use cases

## Interfacing reads

How many times did someone share some data with you in the form of a zip of some nested folders 
whose structure and naming choices are fascinatingly obscure? And how much time do you then spend to write code 
to interface with that freak of nature? Well, one of the intents of py2store is to make that easier to do. 
You still need to understand the structure of the data store and how to deserialize these datas into python 
objects you can manipulate. But with the proper tool, you shouldn't have to do much more than that.

## Thinking about storage later, if ever

You have a new project or need to write a new app. You'll need to store stuff and read stuff back. 
Stuff: Different kinds of resources that you'll app will need to function. Some people enjoy thinking 
of how to optimize that aspect. I don't. I'll leave it to the experts to do so when the time comes. 
Often though, the time is later, if even the time comes. So instead, I'd like to just get on with the business 
logic and write my program. So what I need is an easy way to get some minimal storage functionality. 
But when the time comes to optimize, I shouldn't have to change my code, but instead just change the way my 
DAO does things. What I need is py2store.

# Some links

ORM: Object-relational mapping: https://en.wikipedia.org/wiki/Object-relational_mapping
DAO: Data access object: https://en.wikipedia.org/wiki/Data_access_object
