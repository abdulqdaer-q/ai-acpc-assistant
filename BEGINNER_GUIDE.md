# Beginner Guide

This guide is based on the extracted ACPC camp memory in `final_memory.json` and `chunk_summaries.json`.

The camp memory covers 47,144 messages from March 3, 2025 to March 27, 2026. The repeated beginner themes were:
- understanding the problem statement before coding
- debugging and fixing runtime or compilation issues
- sorting, arrays, strings, and STL basics
- handling edge cases and integer overflow
- learning binary search, graphs, and dynamic programming gradually

## 1. What ACPC Training Is Really About

ACPC training is not mainly about memorizing solutions.

It is about learning how to:
- read a problem carefully
- identify constraints
- choose the correct time complexity
- implement cleanly in C++
- test edge cases before submitting

The camp memory shows this repeatedly: many questions were not about hard algorithms first, but about reading the statement correctly, fixing indexing bugs, choosing the right container, or understanding why a sorted approach was needed.

## 2. Start With a Stable C++ Setup

One repeated issue in the camp was simple environment mistakes.

Use:
- `C++17`
- spaces instead of mixed tabs when formatting code
- the correct headers like `<algorithm>`, `<vector>`, `<set>`, `<map>`, `<string>`

Your base template can start like this:

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    return 0;
}
```

For beginners, this is enough. Do not overbuild your template early.

## 3. The First 5 Things To Check In Any Problem

Before coding, answer these questions:

1. What is the exact input and exact output?
2. What are the constraints on `n`, values, and number of test cases?
3. Is brute force acceptable, or do I need something like `O(n log n)`?
4. Are there edge cases like `n = 0`, `n = 1`, duplicates, negatives, or overflow?
5. Does sorting or counting simplify the problem?

This matches the camp memory very closely. A large fraction of beginner mistakes came from skipping one of these checks.

## 4. The Best First Topics

Based on the camp discussions, beginners should master these in order.

### Arrays, Strings, and Loops

Learn to:
- traverse arrays safely
- count characters and frequencies
- compare strings
- reverse strings
- use conditions carefully

Typical beginner tasks from the memory:
- pangram or character counting problems
- sorting integers
- simple string manipulation

### STL Basics

Get comfortable with:
- `vector`
- `string`
- `pair`
- `set`
- `map`
- `sort`

Do not use a container just because it exists. The camp repeatedly compared simple arrays, vectors, sets, and maps depending on what the problem actually needed.

### Sorting

Sorting appeared everywhere in the camp memory.

When a problem asks about:
- closest values
- grouping equal items
- minimum difference
- ordering before checking conditions

try asking yourself: “Does sorting make the logic obvious?”

### Frequency Arrays and Sets

This was one of the most common beginner patterns in the memory.

Use it for:
- counting letters
- checking distinct values
- pangram-style problems
- duplicate detection

### Binary Search

Do not jump into it too early, but start once you are comfortable with arrays and sorting.

Use binary search when:
- the array is sorted
- you need first/last valid position
- the answer is monotonic

The camp memory also shows many confusions around `lower_bound`, duplicates, and boundaries. Learn those carefully.

## 5. Common Beginner Mistakes Seen In The Camp

These came up again and again.

### Not Reading Constraints

If `n` is large, `O(n^2)` may fail.

Always estimate:
- `10^3` can often handle quadratic work
- `10^5` usually needs `O(n log n)` or `O(n)`

### Using `int` When `long long` Is Needed

The memory contains repeated overflow discussions, especially with values near `10^18`.

If multiplication or large sums are involved, think about `long long` first.

### Missing Edge Cases

Common misses:
- empty or size-1 cases
- all equal values
- duplicates near a boundary
- already sorted input
- negative values

### Runtime Errors From Bad Indexing or Array Size

Typical causes:
- reading outside array bounds
- allocating too little memory
- assuming input always has the shape you expect

### Compilation Problems

The camp memory repeatedly mentioned:
- wrong compiler version
- missing include files
- typo-level syntax issues

These are easy to fix, but only if you slow down and read the error message carefully.

## 6. A Good Debugging Routine

Debugging was one of the most repeated topics in the memory.

Use this checklist:

1. Test the smallest possible case.
2. Test a normal case.
3. Test a tricky edge case.
4. Print intermediate values if the logic is unclear.
5. Check array bounds and loop conditions.
6. Re-read the statement after every wrong answer.

A lot of algorithm bugs in beginner code are actually statement misunderstandings.

## 7. How To Think About Solutions

A useful beginner path from the camp style is:

1. Write the brute-force idea in words.
2. Check whether it fits the constraints.
3. Ask what structure the problem gives you.
   Examples: sorted order, frequency counts, prefix information, graph edges, monotonic answer.
4. Pick one clean approach.
5. Test before submitting.

This is much better than memorizing random templates.

## 8. When To Learn Harder Topics

After you are comfortable with arrays, strings, sorting, and debugging, move to:
- two pointers
- prefix sums
- binary search
- graphs with BFS and DFS
- basic dynamic programming

The camp memory shows these topics appearing often, but beginners do better when they build the base first.

## 9. How To Use AI Correctly

This also appeared early in the camp discussions.

Good usage:
- ask for a hint
- ask why your solution gets WA, RE, or TLE
- ask for help understanding complexity or edge cases

Bad usage:
- pasting a problem and copying full code without understanding it

The best mentorship style is:
- understand the idea
- implement it yourself
- ask for review if it fails

## 10. A Realistic 4-Week Beginner Plan

### Week 1

Focus on:
- input/output
- loops
- conditions
- arrays
- strings

Practice:
- counting
- minimum/maximum
- simple simulation

### Week 2

Focus on:
- vectors
- sorting
- sets and maps
- frequency counting

Practice:
- pangram-type tasks
- duplicate detection
- ordering-based problems

### Week 3

Focus on:
- time complexity
- binary search basics
- two pointers
- prefix sums

Practice:
- sorted array queries
- window/range tasks

### Week 4

Focus on:
- BFS/DFS basics
- introductory DP
- debugging under contest conditions

Practice:
- simple graph traversal
- small-state DP

## 11. What Good Progress Looks Like

You are progressing if:
- you can explain your solution before coding it
- you notice edge cases earlier
- you understand why `sort` or `set` helps
- you debug your own code faster
- you can tell when brute force is too slow

That is a better signal than simply solving a few random hard problems.

## 12. Final Advice

From the camp memory, the strongest repeated pattern was this:

The students who improved were not the ones who rushed to code first. They were the ones who:
- read carefully
- asked why
- tested edge cases
- learned from wrong answers
- kept their code simple

Start simple. Build strong basics. Then add harder topics one layer at a time.
