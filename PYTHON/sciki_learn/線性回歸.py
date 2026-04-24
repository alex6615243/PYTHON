from sklearn.linear_model import LinearRegression
import numpy as np
import matplotlib.pyplot as plt

x = np.array([i for i in range(100)])
y = 12*x + 100 *np.random.randn(100)

A = x.reshape(100,1)
model = LinearRegression()
model.fit(A,y)
y_predict = model.predict(A)
plt.scatter(x,y)
plt.plot(x,y_predict,'r')
plt.scatter(30,model.predict([[30]]),c = 'r',marker='^')
plt.show()
