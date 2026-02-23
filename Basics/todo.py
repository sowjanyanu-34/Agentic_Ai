'''
Write  a python program where
ask user to add task to the pending list
after user types the task 
add it to the python list and greet user
with want to add more task ? or exit
'''
tasks=[]
while True:
    print("Hello do you want to any task")
    user_task=input("")
    tasks.append(user_task)
    print("Do you want to add more task ? or exit")
    choice=input("")
    if (choice=='no'):
        break
    print("Tasks added:")
    print(tasks)