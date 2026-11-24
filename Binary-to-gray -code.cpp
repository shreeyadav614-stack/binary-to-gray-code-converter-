#include <iostream>
#include <string>
using namespace std;

// Function to check whether input is binary
bool isBinary(string num) {
    if (num.empty())
        return false;

    for (char bit : num) {
        if (bit != '0' && bit != '1')
            return false;
    }
    return true;
}

// Convert Binary to Gray Code
string binaryToGray(string binary) {
    string gray = "";
    gray += binary[0];

    for (int i = 1; i < binary.length(); i++) {
        if (binary[i] == binary[i - 1])
            gray += '0';
        else
            gray += '1';
    }

    return gray;
}

// Convert Gray Code to Binary
string grayToBinary(string gray) {
    string binary = "";
    binary += gray[0];

    for (int i = 1; i < gray.length(); i++) {
        if (binary[i - 1] == gray[i])
            binary += '0';
        else
            binary += '1';
    }

    return binary;
}

int main() {
    int choice;
    string number;

    do {
        cout << "\n===== BINARY-GRAY CODE CONVERTER =====\n";
        cout << "1. Binary to Gray Code\n";
        cout << "2. Gray Code to Binary\n";
        cout << "3. Exit\n";
        cout << "Enter your choice: ";
        cin >> choice;

        if (choice == 1 || choice == 2) {
            cout << "Enter the binary/Gray code: ";
            cin >> number;

            if (!isBinary(number)) {
                cout << "Invalid input! Enter only 0 and 1.\n";
                continue;
            }

            if (choice == 1) {
                cout << "Binary Code : " << number << endl;
                cout << "Gray Code   : "
                     << binaryToGray(number) << endl;
            } else {
                cout << "Gray Code   : " << number << endl;
                cout << "Binary Code : "
                     << grayToBinary(number) << endl;
            }
        } else if (choice == 3) {
            cout << "Program terminated. Thank you!\n";
        } else {
            cout << "Invalid choice! Try again.\n";
        }

    } while (choice != 3);

    return 0;
}
