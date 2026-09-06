CXX ?= g++
CXXFLAGS ?= -std=c++17 -O0 -g -Wall -Wextra -Werror -I include
BIN := host_test/duty_cycle_test

.PHONY: test clean

test: $(BIN)
	./$(BIN)

$(BIN): src/duty_cycle.cpp include/duty_cycle.hpp host_test/test_duty_cycle.cpp
	$(CXX) $(CXXFLAGS) src/duty_cycle.cpp host_test/test_duty_cycle.cpp -o $(BIN)

clean:
	rm -f $(BIN)
