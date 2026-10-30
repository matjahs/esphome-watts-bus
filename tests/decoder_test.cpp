#include "decoder.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <set>
#include <string>
#include <vector>

using esphome::watts_bus::Edge;
using esphome::watts_bus::FrameDecoder;
using esphome::watts_bus::WattsMessage;

/**
 * @brief Tracks the number of failed test assertions in the decoder test suite.
 *
 * This variable is incremented whenever a test condition evaluated using the
 * `CHECK` macro fails. It is used to provide a summary of the total number of
 * failed checks at the conclusion of the test run.
 *
 * @note This variable is scoped to the current translation unit (`static`
 * ensures it is not accessible outside this file).
 */
static int failures = 0;

// Minimal assert that keeps going, so one run shows every failure.
#define CHECK(cond)                                               \
  do {                                                            \
    if (!(cond)) {                                                \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
      failures++;                                                 \
    }                                                             \
  } while (0)

static bool near(float a, float b) { return std::fabs(a - b) < 0.01f; }

// "# gap N us" = idle (high) line held for N us; "L D" = level L held for D us.
static std::vector<Edge> load_fixture(const std::string &name) {
    std::vector<Edge> edges;
    std::ifstream in(std::string(FIXTURE_DIR) + "/" + name);
    std::string line;

    while (std::getline(in, line)) {
        unsigned long duration = 0;
        unsigned level = 0;

        // Try "# gap N us"
        // Format: starts with "# gap ", then integer, then " us"
        {
            const char *s = line.c_str();
            const char *prefix = "# gap ";
            if (std::strncmp(s, prefix, std::strlen(prefix)) == 0) {
                const char *p = s + std::strlen(prefix);

                char *endp = nullptr;
                errno = 0;
                unsigned long v = std::strtoul(p, &endp, 10);

                // endp must advance and parse must succeed, and after number should be " us"
                if (errno == 0 && endp != p) {
                    const char *rest = endp;
                    while (*rest == ' ' || *rest == '\t') rest++;
                    if (std::strncmp(rest, " us", 3) == 0 || std::strncmp(rest, "us", 2) == 0) {
                        duration = v;
                        edges.push_back({1, static_cast<uint32_t>(duration)});
                        continue;
                    }
                }
            }
        }

        // Try "L D" where L <= 1
        // We'll parse two unsigned ints separated by whitespace.
        {
            const char *s = line.c_str();
            auto skip_ws = [&](const char *&p) {
                while (*p == ' ' || *p == '\t') ++p;
            };

            skip_ws(s);

            char *endp = nullptr;
            errno = 0;
            unsigned long l = std::strtoul(s, &endp, 10);
            if (!(errno == 0 && endp != s)) {
                continue; // not parseable
            }

            const char *p = endp;
            skip_ws(p);

            errno = 0;
            unsigned long d = std::strtoul(p, &endp, 10);
            if (!(errno == 0 && endp != p)) {
                continue; // not parseable
            }

            level = static_cast<unsigned>(l);
            duration = d;

            // Match original condition: level <= 1
            if (level <= 1) {
                edges.push_back({static_cast<uint8_t>(level), static_cast<uint32_t>(duration)});
            }
        }
    }

    return edges;
}

static std::vector<WattsMessage> decode_all(const std::vector<Edge> &edges) {
    FrameDecoder decoder;
    std::vector<WattsMessage> out;
    WattsMessage msg{};
    for (const Edge &edge: edges) {
        decoder.push(edge);
        if (decoder.pop(msg)) out.push_back(msg);
    }
    decoder.flush();
    if (decoder.pop(msg)) out.push_back(msg);
    return out;
}

static void print(const WattsMessage &m) {
    std::printf("  %04X  %5.1f C  set %5.1f C  demand %3u  |", m.id, m.temperature, m.setpoint,
                m.heat_demand);
    for (uint8_t b: m.raw) std::printf(" %02X", b);
    std::printf("\n");
}

static void print_all(const char *title, const std::vector<WattsMessage> &msgs) {
    std::printf("%s (%zu messages)\n", title, msgs.size());
    for (const WattsMessage &m: msgs) print(m);
}

// True if any message matches id + setpoint.
static bool has(const std::vector<WattsMessage> &msgs, uint16_t id, float setpoint) {
    return std::any_of(msgs.begin(), msgs.end(), [&](const WattsMessage &m) {
        return m.id == id && near(m.setpoint, setpoint);
    });
}

static void check_no_duplicates(const std::vector<WattsMessage> &msgs) {
    for (size_t i = 1; i < msgs.size(); i++)
        CHECK(msgs[i].raw != msgs[i - 1].raw);
}

static void test_setpoints() {
    auto msgs = decode_all(load_fixture("watts-capture-setpoints.txt"));
    print_all("setpoints", msgs);

    CHECK(msgs.size() == 7); // 14 frames = 7 confirmed pairs
    CHECK(!msgs.empty() && msgs[0].id == 0x4572);
    CHECK(!msgs.empty() && near(msgs[0].temperature, 21.5f) && near(msgs[0].setpoint, 18.0f));

    // Office: each change is reported twice (toggle differs), so drop repeats of the same setpoint.
    std::vector<WattsMessage> office;
    for (const WattsMessage &m: msgs) {
        if (m.id != 0x4584) continue;
        if (!office.empty() && near(office.back().setpoint, m.setpoint)) continue;
        office.push_back(m);
    }
    CHECK(office.size() == 3);
    if (office.size() == 3) {
        CHECK(near(office[0].setpoint, 20.0f) && near(office[0].temperature, 23.6f));
        CHECK(near(office[1].setpoint, 16.0f) && near(office[1].temperature, 23.7f));
        CHECK(near(office[2].setpoint, 18.0f) && near(office[2].temperature, 23.8f));
    }
    check_no_duplicates(msgs);
}

static void test_long() {
    auto msgs = decode_all(load_fixture("watts-capture-long.txt"));
    print_all("long", msgs);

    std::set<uint16_t> ids;
    for (const WattsMessage &m: msgs) ids.insert(m.id);
    CHECK((ids == std::set<uint16_t>{0x4584, 0x4572, 0x456E, 0x702D}));

    CHECK(std::any_of(msgs.begin(), msgs.end(), [](const WattsMessage &m) {
        return m.id == 0x456E && near(m.setpoint, 22.0f) && m.heat_demand == 100;
        }));
    CHECK(has(msgs, 0x702D, 19.5f));
    CHECK(has(msgs, 0x4572, 17.0f));
    check_no_duplicates(msgs);
}

static void test_first_capture() {
    auto msgs = decode_all(load_fixture("watts-capture.txt"));
    print_all("first capture", msgs);

    CHECK(has(msgs, 0x702D, 19.0f));
    check_no_duplicates(msgs);
}

static void test_single_copy_is_not_confirmed() {
    auto edges = load_fixture("watts-capture-setpoints.txt");

    // Keep the leading gap and the first frame, stop at the next gap.
    std::vector<Edge> one_frame{edges[0]};
    for (size_t i = 1; i < edges.size() && !(edges[i].level == 1 && edges[i].duration_us > 5000); i++) {
        one_frame.push_back(edges[i]);
    }
    one_frame.push_back({1, 10'000'000}); // 10 s of silence

    CHECK(decode_all(one_frame).empty());
}

int main() {
    test_setpoints();
    test_long();
    test_first_capture();
    test_single_copy_is_not_confirmed();

    std::printf(failures == 0 ? "ALL PASSED\n" : "%d FAILURE(S)\n", failures);
    return failures == 0 ? 0 : 1;
}
