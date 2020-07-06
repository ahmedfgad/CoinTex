# Game Playing Agent for CoinTex using Genetic Algorithm
This project builds a game playing agent that plays CoinTex. CoinTex is a cross-platform open-source game developed in Python using a framework called [Kivy](https://kivy.org). 

The source code of CoinTex is available at the root of the [CoinTex GitHub project](https://github.com/ahmedfgad/CoinTex). Being developed in Kivy, CoinTex is available for Android at [Google Play](https://play.google.com/store/apps/details?id=coin.tex.cointexreactfast&hl=en).

https://play.google.com/store/apps/details?id=coin.tex.cointexreactfast&hl=en

The agent is created using the genetic algorithm (GA). The [PyGAD](https://pygad.readthedocs.io) library is used to build the GA. 

# Installing PyGAD

[PyGAD](https://pygad.readthedocs.io) is the library used for building the genetic algorithm (GA). Check the documentation at [Read the Docs](https://pygad.readthedocs.io) to get started.

The minimum PyGAD version that works with this project is 2.4.0. A lower version does not support 2 features that are necessary in this work which are:

1. The `delay_after_gen` parameter in the `pygad.GA` class's constructor that puts the GA into sleep for a number of seconds after each generation.
2. The function passed to the `callback_generation` parameter of the `pygad.GA` class's constructor returns the string `stop` returned to stop the GA before visiting all the generations.

[PyGAD](https://pygad.readthedocs.io) can be installed from [PyPI](https://pypi.org/project/pygad) using the `pip` installer. For Windows, use the following CMD command:

```
pip install pygad
```

For Linux and Mac, replace `pip`  by `pip3` because PyGAD uses Python 3:

```
pip3 install pygad
```

Once being installed, make sure it works well by importing it. The latest version at the time of writing this tutorial is **2.4.0** or higher. 

```python
import pygad

print(pygad.__version__)
```

# Run the Project

To run the project, just run the `main.py` file.

In Windows, use this CMD command:

```
python main.py
```

For Linux/Mac, use `python3` rather than `python`:

```
python3 main.py
```

A window appears like the shows below. Normally, the game only activates the levels that the user completed successfully plus 1 more level. Specially for this project, all the levels are activated. 

![CoinTex-2020-07-06_15-34-51](https://user-images.githubusercontent.com/16560492/86599324-c50e2d00-bf9e-11ea-8801-51f2b41c4f4f.jpg)

After the main screen of the app appears, select any of the activated levels and the agent will play it automatically [hoping to pass the level successfully].

![2020-07-05_19-59-17](https://user-images.githubusercontent.com/16560492/86600094-dad02200-bf9f-11ea-9513-5b57739b0f58.gif)

# For More Information

The game is developed in Kivy. To get started with Kivy, check the following resources:

## Tutorial: [Python for Android: Start Building Kivy Cross-Platform Applications](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad)

This tutorial titled [Python for Android: Start Building Kivy Cross-Platform Applications](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad) covers the steps for creating an Android app out of the Kivy app.

[![Kivy-Tutorial](https://user-images.githubusercontent.com/16560492/86205332-dfdd3d80-bb69-11ea-91fb-cb0143cb1e5e.png)](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad)

## Book: [Building Android Apps in Python Using Kivy with Android Studio](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303)

To get started with Kivy app development and how to built Android apps out of the Kivy app, check the book titled [Building Android Apps in Python Using Kivy with Android Studio](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303).

The CoinTex game is 100% documented in chapters 5 and 6 of [this book](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303). It starts from a hello world app until building CoinTex.

[![kivy-book](https://user-images.githubusercontent.com/16560492/86205093-575e9d00-bb69-11ea-82f7-23fef487ce3c.jpg)](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303)

# For Contacting the Author

* E-mail: [ahmed.f.gad@gmail.com](mailto:ahmed.f.gad@gmail.com)
* [LinkedIn](https://www.linkedin.com/in/ahmedfgad)
* [Amazon Author Page](https://amazon.com/author/ahmedgad)
* [Heartbeat](https://heartbeat.fritz.ai/@ahmedfgad)
* [Paperspace](https://blog.paperspace.com/author/ahmed)
* [KDnuggets](https://kdnuggets.com/author/ahmed-gad)
* [TowardsDataScience](https://towardsdatascience.com/@ahmedfgad)
* [GitHub](https://github.com/ahmedfgad)
