#include "gridSequence.h"
#include "gridConfig.h"

namespace {

int redValues[kNumStims];
int greenValues[kNumStims];

int coordinates[kNumStims][2];  // base diagonal traversal, 1-based (x, y)
int oriented[kNumStims][2];     // after applying the start-corner flip

int imin(int a, int b) { return a < b ? a : b; }

// Walk the kNumSteps x kNumSteps grid one anti-diagonal at a time, alternating
// direction along each diagonal (a boustrophedon order), starting from (1, 1).
void buildDiagonalOrder() {
  int count = 0;
  int d = 2;  // diagonal index (x + y)
  while (count < kNumStims) {
    if (d % 2 == 1) {
      for (int x = 1; x <= imin(d - 1, kNumSteps); x++) {
        int y = d - x;
        if (y > 0 && y <= kNumSteps) {
          coordinates[count][0] = x;
          coordinates[count][1] = y;
          count++;
        }
        if (count >= kNumStims) break;
      }
    } else {
      for (int y = 1; y <= imin(d - 1, kNumSteps); y++) {
        int x = d - y;
        if (x > 0 && x <= kNumSteps) {
          coordinates[count][0] = x;
          coordinates[count][1] = y;
          count++;
        }
        if (count >= kNumStims) break;
      }
    }
    d++;
  }
}

// Flip X and/or Y so the traversal starts from the requested corner.
void applyOrder(int order) {
  for (int i = 0; i < kNumStims; i++) {
    int x = coordinates[i][0];
    int y = coordinates[i][1];
    switch (order) {
      case 2: y = kNumSteps + 1 - y; break;
      case 3: x = kNumSteps + 1 - x; break;
      case 4: x = kNumSteps + 1 - x; y = kNumSteps + 1 - y; break;
      case 1:
      default: break;
    }
    oriented[i][0] = x;
    oriented[i][1] = y;
  }
}

// Linearly spaced value: minValue at stepIndex 0, maxValue at kNumSteps-1.
int linspace(int minValue, int maxValue, int stepIndex) {
  return minValue + (long)(maxValue - minValue) * stepIndex / (kNumSteps - 1);
}

}  // namespace

void gridSequenceBuild(int order, int minRed, int maxRed, int minGreen, int maxGreen) {
  buildDiagonalOrder();
  applyOrder(order);
  for (int i = 0; i < kNumStims; i++) {
    redValues[i]   = linspace(minRed, maxRed, oriented[i][0] - 1);
    greenValues[i] = linspace(minGreen, maxGreen, oriented[i][1] - 1);
  }
}

int gridSequenceCount() { return kNumStims; }
int gridSequenceRed(int index) { return redValues[index]; }
int gridSequenceGreen(int index) { return greenValues[index]; }
