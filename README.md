# simple-sim
A proof-of-concept simulator for Slay the Spire combat(s). 
Accurately simulates a combat in the game Slay the Spire to prove it can be unwinnable for the player.  

Brute-forces all possible outcomes of card play, accounting for order and fixed shuffle RNG.  
Implements the default starter deck on A10+ and the Gremlin Nob attack pattern for A18+.  
Implements several cards considered "unhelpful" for the purposes of surviving the combat.  

Includes options to display results of multiple combats in a 3-dimensional historgram as plaintext.  
Also includes options to specify results of shuffle RNG if a specific RNG seed is tested.  
