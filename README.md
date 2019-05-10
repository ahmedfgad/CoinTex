# CoinTex: Cross-platform multi-level game created in Python using Kivy
CoinTex is a multi-level adventure game created using the **Kivy** cross-platform Python framework. The game is successfully tested in Linux, Windows, and Android and working on all of these platforms without even changing a single line of code. Here is a simple description of it.

The game is multi-level. Once it is opened, a main screen appears that shows a matrix of all game levels, which are 24 up to this time. The main screen is given in the next figure. 

https://user-images.githubusercontent.com/16560492/57524758-14b88080-7329-11e9-809a-09d7bb08204b.jpg

There will be only 1 level activated which is level 1. Once level x is completed, the level x+1 will be activated until reaching the last level. Information about the latest level completed is stored in a file named "game_info". This file is created once level 1 is completed. If this file is removed, the game will return back to the initial state in whicih only level 1 is activated. By pressing a level, the user is directed to another screen where the player can start playing the game. The screen of level 1 is
given below.

https://user-images.githubusercontent.com/16560492/57524794-36196c80-7329-11e9-9c2d-43e09d08197e.jpg

Supposing that level 1 is completed successfully, level 2 will be activated in the main screen as given below.

https://user-images.githubusercontent.com/16560492/57525130-323a1a00-732a-11e9-877a-9366c65ac7d2.jpg

The game has a character that moves freely according to the touch position on the screen. The player has a time-unlimited mission which is collecting a number of coins that are randomly distributed on the screen. A coin is collected when there is a collision with it and the character. As shown in the previous figure, a text at the top-left of the screen shows the number of collected coins and the total number of coins in the current level. The first level has just 5 coins and the statein which 2 coins are collected is given in the next figure. Once all coins are collected, the level completes and the user is directed to the main screen where the next level is active for being played.

https://user-images.githubusercontent.com/16560492/57524900-87296080-7329-11e9-950e-7541501c3008.jpg

Collecting the coins is not that easy because there are monsters and thrown fire that struggle the player's way of completing the level. Their motion are not expected and thus it tests the player's ability to do fast reactions in order to avoid their collision. Some levels might have only monsters, others may have only fire, and others may have a combination. When the player collides a monster or a fire, its health reduces by a percentage that is proportinal to the collision time. There is a red bar at the top of the screen that reflects the current health of the player. he next figure shows the red bar after collision occurs.

https://user-images.githubusercontent.com/16560492/57525255-804f1d80-732a-11e9-81f3-20c55550cbff.jpg

The much time the player collides with a monster or a fire the much reduction in its health. When the health is zero, the player dies as given below. 

https://user-images.githubusercontent.com/16560492/57525269-87762b80-732a-11e9-9e26-999e17322452.jpg
