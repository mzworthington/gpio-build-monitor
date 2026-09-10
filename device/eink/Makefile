CXX ?= g++
CXXFLAGS ?= -std=c++17 -O0 -g -Wall -Wextra -Werror -I include
BIN := host_test/duty_cycle_test

.PHONY: test clean

test: $(BIN)
	./$(BIN)

$(BIN): src/duty_cycle.cpp src/client.cpp include/duty_cycle.hpp include/client.hpp include/status_view.hpp include/bq27220.hpp include/power_control.hpp host_test/test_duty_cycle.cpp
	$(CXX) $(CXXFLAGS) src/duty_cycle.cpp src/client.cpp host_test/test_duty_cycle.cpp -o $(BIN)

clean:
	rm -f $(BIN)
