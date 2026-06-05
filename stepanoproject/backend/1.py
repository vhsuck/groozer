import bcrypt, sys
print(sys.executable)
print(bcrypt.__file__)
print(getattr(bcrypt, "__version__", None))
print("has __about__:", hasattr(bcrypt, "__about__"))