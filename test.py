m=0

for a in range(1,1000):

  flag=True

  for x in range(1,1000):
    for y in range(1,1000):
      con=((x<5)<=(x**2<a))
      con2=((y**2 <= a)<=(y<=5))
      con3=con and con2

      if not(con3):
        flag=False
        break

  if flag:
    m+=1

print(m)