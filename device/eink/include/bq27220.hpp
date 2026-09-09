#pragma once

#include <cstdint>

namespace bq27220 {

// TI BQ27220 Current (0x0C): positive = charge into the cell.
inline bool is_charging(int16_t current_ma) { return current_ma > 0; }

}  // namespace bq27220
