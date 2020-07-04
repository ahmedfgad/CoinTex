# CoinTex: Cross-platform Multi-Level Game created in Python using Kivy
CoinTex is a multi-level adventure game created using the **Kivy** cross-platform Python framework. The game is successfully tested in Linux, Windows, and Android and working on all of these platforms without even changing a single line of code. Here is a simple description of it.

# Game Description

The game is multi-level. Once it is opened, the main screen appears that shows a matrix of all game levels, which are 24 up to this time. The main screen is given in the next figure. 

![1](https://user-images.githubusercontent.com/16560492/57524758-14b88080-7329-11e9-809a-09d7bb08204b.jpg)

There will be only 1 level activated which is level 1. Once level x is completed, the level x+1 will be activated until reaching the last level. Information about the latest level completed is stored in a file named "game_info". This file is created once level 1 is completed. If this file is removed, the game will return back to the initial state in which only level 1 is activated. By pressing a level, the user is directed to another screen where the player can start playing the game. The screen of level 1 is
given below.

![1](https://user-images.githubusercontent.com/16560492/57524794-36196c80-7329-11e9-9c2d-43e09d08197e.jpg)

Supposing that level 1 is completed successfully, level 2 will be activated on the main screen as given below.

![1](https://user-images.githubusercontent.com/16560492/57525130-323a1a00-732a-11e9-877a-9366c65ac7d2.jpg)

The game has a character that moves freely according to the touch position on the screen. The player has a time-unlimited mission which is collecting a number of coins that are randomly distributed on the screen. A coin is collected when there is a collision with it and the character. As shown in the previous figure, a text at the top-left of the screen shows the number of collected coins and the total number of coins at the current level. 

The first level has just 5 coins. The next figure shows how it looks like after 2 coins are collected. Once all coins are collected, the level completes and the user is directed to the main screen where the next level is active for being played.

![1](https://user-images.githubusercontent.com/16560492/57524900-87296080-7329-11e9-950e-7541501c3008.jpg)

Collecting the coins is not that easy because there are monsters and thrown fire that struggles the player's way of completing the level. Their motion is not expected and thus it tests the player's ability to do fast reactions in order to avoid their collision. 

Some levels might have only monsters, others may only have fire, and others may have a combination. When the player collides a monster or a fire, its health reduces by a percentage that is proportional to the collision time. There is a red bar at the top of the screen that reflects the current health of the player. he next figure shows the red bar after a collision occurs.

![1](https://user-images.githubusercontent.com/16560492/57525255-804f1d80-732a-11e9-81f3-20c55550cbff.jpg)

The much time the player collides with a monster or a fire the much reduction in its health. When the health is zero, the player dies as given below. 

![1](https://user-images.githubusercontent.com/16560492/57525269-87762b80-732a-11e9-9e26-999e17322452.jpg)

Note that the game includes some **sound effects**. There is also background music running while the main screen is open or any level is being played.

# Running the Project for Developers

Before running the game, you have to make sure Kivy is installing and running successfully. To get started with Kivy, check the resources given below:

## Tutorial: [Python for Android: Start Building Kivy Cross-Platform Applications](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad)

This tutorial titled [Python for Android: Start Building Kivy Cross-Platform Applications](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad) covers the steps for creating an Android app out of the Kivy app.

[![Kivy-Tutorial](https://user-images.githubusercontent.com/16560492/86205332-dfdd3d80-bb69-11ea-91fb-cb0143cb1e5e.png)](https://www.linkedin.com/pulse/python-android-start-building-kivy-cross-platform-applications-gad)

## Book: [Building Android Apps in Python Using Kivy with Android Studio](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303)

To get started with Kivy app development and how to built Android apps out of the Kivy app, check the book titled [Building Android Apps in Python Using Kivy with Android Studio](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303). This book documents the CoinTex game from A to Z in chapters 5 and 6.

[![kivy-book](https://user-images.githubusercontent.com/16560492/86205093-575e9d00-bb69-11ea-82f7-23fef487ce3c.jpg)](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303)

After making sure Kivy is running, just use the next terminal command to run the main file of the game **main.py**. The game is developed in Python 3 and so the terminal command **python3** is used for Linux/Mac.

`ahmed-gad@ubuntu:~/Desktop/CoinTex$ python3 main.py`

For Android, the APK file is built using Buildozer and this is why the **buildozer.spec** file exists in the project. Just use this terminal command for exporting the APK file. 

After it runs successfully, the APK file will be exported. For more information about installing Buildozer, generating, and locating the APK file, you can read the tutorial and [chapter 8 of the book mentioned above](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303).

`ahmed-gad@ubuntu:~/Desktop/CoinTex$ buildozer android release deploy run`

# Running the Game for End Users

The game is already distributed for end-user to download and run easily for Android and Linux. For Linux, it is available at [this link](https://www.linux-apps.com/p/1279788). 

For Android, it is available at [Google Play](https://play.google.com/store/apps/details?id=coin.tex.cointexreactfast).

# Game Documentation

The CoinTex game is 100% documented in chapters 5 and 6 of the book titled [Building Android Apps in Python Using Kivy with Android Studio](https://www.amazon.com/Building-Android-Python-Using-Studio/dp/1484250303). It starts from a hello world app until building CoinTex.

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
