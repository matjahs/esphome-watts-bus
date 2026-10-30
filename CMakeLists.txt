cmake_minimum_required(VERSION 3.20)
project(esphome_watts_bus CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_testing()

# Host-side test of the pure decoder; ESPHome itself never uses this file.
add_executable(decoder_test
  tests/decoder_test.cpp
  components/watts_bus/decoder.cpp
        components/watts_bus/decoder.h
)
target_include_directories(decoder_test PRIVATE components/watts_bus)
target_compile_definitions(decoder_test PRIVATE
  FIXTURE_DIR="${CMAKE_SOURCE_DIR}/tests/fixtures"
)
target_compile_options(decoder_test PRIVATE -Wall -Wextra -Wpedantic)

add_test(NAME decoder_test COMMAND decoder_test)
