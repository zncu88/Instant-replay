from tkinter import *
root = Tk()
root.geometry('800x500')
root.title('Screen Capture')
root.resizable(False, False)

button1 = Button(root, text='Button 1',width=5,height=2)
button1.grid(column=0, row=0, columnspan=2,ipadx=5)



button2 = Button(root, text='Button 2',width=5,height=2)
button2.grid(column=2, row=0, columnspan=2,ipadx=5)


button3 = Button(root, text='Button 3',width=5,height=2)
button3.grid(column=4, row=0, columnspan=2,ipadx=5)


root.mainloop()