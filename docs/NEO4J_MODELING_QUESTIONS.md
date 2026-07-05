# Neo4j Graph Modeling Questions

These exercises focus on designing a Neo4j graph schema from requirements.
For each case, identify:
- node labels and properties
- relationship types and directions
- relationship properties if needed

## Question 1 — Employee training platform

A company runs an internal training platform where employees can enroll in courses.
The platform must support these queries efficiently:
- Which courses has a given employee completed, and what score did they get?
- Which employees are currently enrolled in a given course?
- Which instructor teaches a given course?
- Which employees share at least one completed course?

Requirements:
- Each employee has a unique identifier, name, and department
- Each course has a unique identifier, title, duration in hours, and difficulty level
- Each instructor has a name and an expertise field
- Track the date when an employee enrolls in a course
- Track the date and score when an employee completes a course
- A course is taught by one instructor

Design the Neo4j graph schema for this platform.

## Question 2 — Music streaming platform

A music streaming service wants to model listeners, songs, and playlists.
The platform must support these queries efficiently:
- Which songs are in a given playlist?
- Which playlists contain a given song?
- Which listeners follow a given artist?
- Which listeners have liked the same songs?

Requirements:
- Each listener has a unique id, username, and country
- Each artist has a unique id, name, and genre
- Each song has a unique id, title, duration, and release year
- Each playlist has a unique id, title, and privacy status
- Track when a listener adds a song to a playlist
- Track when a listener likes a song

Design the Neo4j graph schema for this platform.

## Question 3 — Hospital appointment system

A hospital wants to manage patients, doctors, appointments, and prescriptions.
The platform must support these queries efficiently:
- Which appointments does a given patient have?
- Which doctor is assigned to a given appointment?
- Which prescriptions were written during a given appointment?
- Which patients have visited the same doctor?

Requirements:
- Each patient has a unique id, name, age, and contact information
- Each doctor has a unique id, name, and specialty
- Each appointment has a unique id, date, time, and status
- Each prescription has a unique id, medication name, dosage, and duration
- Track the status of the appointment
- Track the prescription date

Design the Neo4j graph schema for this platform.

## Question 4 — Online learning community

An online learning community wants to model students, posts, comments, and tags.
The platform must support these queries efficiently:
- Which posts did a given student create?
- Which comments belong to a given post?
- Which students reacted to the same post?
- Which posts share at least one tag?

Requirements:
- Each student has a unique id, name, and city
- Each post has a unique id, title, body, and creation time
- Each comment has a unique id, text, and creation time
- Each tag is identified by a name
- Track the type of reaction a student gives to a post
- A comment belongs to exactly one post

Design the Neo4j graph schema for this platform.

## Question 5 — Food delivery application

A food delivery application wants to manage customers, restaurants, orders, and menu items.
The platform must support these queries efficiently:
- Which restaurants does a customer order from most often?
- Which menu items belong to a given restaurant?
- Which orders contain a given menu item?
- Which customers have ordered from the same restaurant?

Requirements:
- Each customer has a unique id, name, and city
- Each restaurant has a unique id, name, category, and rating
- Each order has a unique id, order date, status, and total amount
- Each menu item has a unique id, name, price, and availability
- Track the quantity of each item in an order
- A restaurant offers many menu items

Design the Neo4j graph schema for this platform.

