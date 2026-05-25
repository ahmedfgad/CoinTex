# Game Playing Agent for CoinTex using Genetic Algorithm
This project builds a game playing agent that plays CoinTex. CoinTex is a cross-platform open-source game developed in Python using a framework called [Kivy](https://kivy.org). 

The source code of CoinTex is available at the root of the [CoinTex GitHub project](https://github.com/ahmedfgad/CoinTex). Being developed in Kivy, CoinTex is available for Android at [Google Play](https://play.google.com/store/apps/details?id=coin.tex.cointexreactfast&hl=en).

https://play.google.com/store/apps/details?id=coin.tex.cointexreactfast&hl=en

The only AI used to build the agent is the genetic algorithm (GA). There is no machine/deep learning model used. The [PyGAD](https://pygad.readthedocs.io) library is used to build the GA. 

The agent does not have its own copy of the game. It reuses the main CoinTex
engine in the parent folder (`main.py`, `levels.py`, `graphics.py`, `audio.py`,
`state.py`, `ui.py`), so it always plays the current version of the game with all
of its levels and graphics. The agent file `PlayerGA/main.py` only adds the
genetic algorithm on top of that engine.

# How the Agent Works

The agent picks where the player should walk next and when to shoot.

A solution in the genetic algorithm has two genes, an `[x, y]` target point in the
play area (each value from 0 to 1). The fitness of a target is high when it is
close to the nearest coin and lower when it sits on top of a monster or fire.
After each generation the best target is sent to the player so it walks there,
and the search runs again from the new position. Because coins are collected and
the player keeps moving, the target keeps changing, so every solution is measured
again each generation instead of being cached.

When the nearest monster gets close, the agent fires at it. The game has a limited
amount of ammo per level and aims the shot at the nearest monster on its own, so
the agent only has to decide when to pull the trigger.

# Installing PyGAD

[PyGAD](https://pygad.readthedocs.io) is the library used for building the genetic algorithm (GA). Check the documentation at [Read the Docs](https://pygad.readthedocs.io) to get started.

This version of the project uses PyGAD 3. Install it from [PyPI](https://pypi.org/project/pygad) with `pip`:

```
pip install pygad
```

For Linux and Mac, replace `pip` by `pip3` because PyGAD uses Python 3:

```
pip3 install pygad
```

The agent also needs the same Kivy runtime as the game. Installing the project
requirements covers both:

```
pip install -r PlayerGA/requirements.txt
```

# Run the Project

Run the agent file from the root of the CoinTex project so it can find the engine
in the parent folder.

In Windows, use this CMD command:

```
python PlayerGA/main.py
```

For Linux/Mac, use `python3` rather than `python`:

```
python3 PlayerGA/main.py
```

The normal game menu appears. For this project all of the levels are unlocked so
the agent can play any of them, and this does not change your saved progress in
the real game. Open Play, pick a world and a level, and the agent takes over and
plays it on its own.

This is a video showing how the agent is able to pass multiple levels in CoinTex with varying complexity: https://www.youtube.com/embed/Sp_0RGjaL-0

# For More Information

The game is developed in Kivy and the agent is created using the genetic algorithm. To get started with Kivy, check the following resources:

## Tutorial: [Introduction to Optimization with Genetic Algorithm](https://towardsdatascience.com/introduction-to-optimization-with-genetic-algorithm-2f5001d9964b)

A brief introduction about evolutionary algorithms (EAs) and describes the genetic algorithm (GA) which is one of the simplest random-based EAs.

[![intro-genetic](https://miro.medium.com/max/700/1*l82SVTj3yaMEDI0YbRiqUw.jpeg)](https://towardsdatascience.com/introduction-to-optimization-with-genetic-algorithm-2f5001d9964b)

## Tutorial: [5 Genetic Algorithm Applications Using PyGAD](https://blog.paperspace.com/genetic-algorithm-applications-using-pygad)

This tutorial introduces PyGAD, an open-source Python library for implementing the genetic algorithm and training machine learning algorithms and how to use PyGAD to build 5 genetic algorithm applications.

[![pygad-apps](https://blog.paperspace.com/content/images/size/w2000/2020/06/national-cancer-institute-J28Nn-CDbII-unsplash.jpg)](https://blog.paperspace.com/genetic-algorithm-applications-using-pygad)

## Tutorial: [Genetic Algorithm Implementation in Python](https://towardsdatascience.com/genetic-algorithm-implementation-in-python-5ab67bb124a6)

Implementing the genetic algorithm in Python based on a simple example in which we are trying to maximize the output of an equation. 

[![ga-python](https://miro.medium.com/max/700/1*Ak-j8GUP4FwzzR-YPjxclg.png)](https://towardsdatascience.com/genetic-algorithm-implementation-in-python-5ab67bb124a6)

## Book: [Practical Computer Vision Applications Using Deep Learning with CNNs](https://www.amazon.com/Practical-Computer-Vision-Applications-Learning/dp/1484241665)

Besides being a beginner's guide to deep learning for computer vision, the book titled [Practical Computer Vision Applications Using Deep Learning with CNNs](https://www.amazon.com/Practical-Computer-Vision-Applications-Learning/dp/1484241665) discusses how the genetic algorithm work in addition to building implementation in Python using NumPy. The book also discusses the non-dominated sorting genetic algorithm.

[![gad-book-2018](https://user-images.githubusercontent.com/16560492/78830077-ae7c2800-79e7-11ea-980b-53b6bd879eeb.jpg)](https://www.amazon.com/Practical-Computer-Vision-Applications-Learning/dp/1484241665)

## Tutorial: [Python for Android: Start Building Kivy Cross-Platform Applications](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad)

This tutorial titled [Python for Android: Start Building Kivy Cross-Platform Applications](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad) covers the steps for creating an Android app out of the Kivy app.

[![Kivy-Tutorial](https://user-images.githubusercontent.com/16560492/86205332-dfdd3d80-bb69-11ea-91fb-cb0143cb1e5e.png)](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad)

## Book: [Building Android Apps in Python Using Kivy with Android Studio](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303)

To get started with Kivy app development and how to built Android apps out of the Kivy app, check the book titled [Building Android Apps in Python Using Kivy with Android Studio](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303).

The CoinTex game is 100% documented in chapters 5 and 6 of [this book](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303). It starts from a hello world app until building CoinTex.

[![kivy-book](https://user-images.githubusercontent.com/16560492/86205093-575e9d00-bb69-11ea-82f7-23fef487ce3c.jpg)](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303)

# Citing PyGAD - Bibtex Formatted Citation

If you used PyGAD, please consider adding a citation to the following paper about PyGAD:

```
@misc{gad2021pygad,
      title={PyGAD: An Intuitive Genetic Algorithm Python Library}, 
      author={Ahmed Fawzy Gad},
      year={2021},
      eprint={2106.06158},
      archivePrefix={arXiv},
      primaryClass={cs.NE}
}
```

# For Contacting the Author

* E-mail: [ahmed.f.gad@gmail.com](mailto:ahmed.f.gad@gmail.com)
* [LinkedIn](https://www.linkedin.com/in/ahmedfgad)
* [Amazon Author Page](https://amazon.com/author/ahmedgad)
* [Heartbeat](https://heartbeat.fritz.ai/@ahmedfgad)
* [Paperspace](https://blog.paperspace.com/author/ahmed)
* [KDnuggets](https://kdnuggets.com/author/ahmed-gad)
* [TowardsDataScience](https://towardsdatascience.com/@ahmedfgad)
* [GitHub](https://github.com/ahmedfgad)
